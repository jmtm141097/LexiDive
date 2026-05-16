#!/usr/bin/env python3
"""
epub_traductor.py
-----------------
Procesa un .epub en español e inserta vocabulario en inglés para ayudar
al lector a aprender inglés mientras lee.

Reemplaza palabras españolas por su equivalente en inglés resaltado
con <mark> (sin traducción entre paréntesis):

  "tenía el cabello rubio"  →  "<mark>had</mark> el <mark>hair</mark> rubio"
  "estaba seguro de que"    →  "<mark>was</mark> <mark>safe</mark> de que"

Uso:
    python epub_traductor.py libro.epub
    python epub_traductor.py libro.epub --salida libro_anotado.epub
    python epub_traductor.py libro.epub --intensidad 5

  --intensidad: palabras distintas a reemplazar por fragmento (default: 3)

Requisitos:
    pip install ebooklib beautifulsoup4
"""
import re
import json
import random
import argparse
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString

# ──────────────────────────────────────────────────────────────────────────────
# Diccionario español → inglés
# Formato: "forma_española": ("english", "glosa_entre_paréntesis")
# Incluye formas conjugadas, plurales y variantes para maximizar coincidencias.
# ──────────────────────────────────────────────────────────────────────────────
ES_EN: dict[str, tuple[str, str]] = {

    # ── Frases (van primero, son más largas) ──────────────────────────────────
    "de repente": ("suddenly", "de repente"),
    "en silencio": ("in silence", "en silencio"),
    "a oscuras": ("in the dark", "a oscuras"),
    "por fin": ("at last", "por fin"),
    "en voz alta": ("out loud", "en voz alta"),
    "de nuevo": ("again", "de nuevo"),
    "una vez más": ("once more", "una vez más"),
    "al final": ("in the end", "al final"),
    "por supuesto": ("of course", "por supuesto"),
    "de inmediato": ("at once", "de inmediato"),
    "hace mucho": ("long ago", "hace mucho"),
    "cara a cara": ("face to face", "cara a cara"),
    "uno a uno": ("one by one", "uno a uno"),
    "a tiempo": ("in time", "a tiempo"),
    "sin duda": ("without a doubt", "sin duda"),
    "poco a poco": ("little by little", "poco a poco"),

    # ── Verbos: formas conjugadas (pretérito) ─────────────────────────────────
    "era": ("was", "era"),
    "eran": ("were", "eran"),
    "fue": ("was/went", "fue"),
    "fueron": ("were/went", "fueron"),
    "estaba": ("was", "estaba"),
    "estaban": ("were", "estaban"),
    "estuvo": ("was", "estuvo"),
    "tenía": ("had", "tenía"),
    "tenían": ("had", "tenían"),
    "tuvo": ("had", "tuvo"),
    "tuvieron": ("had", "tuvieron"),
    "había": ("there was", "había"),
    "habían": ("there were", "habían"),
    "hizo": ("did/made", "hizo"),
    "hicieron": ("did/made", "hicieron"),
    "dijo": ("said", "dijo"),
    "dijeron": ("said", "dijeron"),
    "vio": ("saw", "vio"),
    "vieron": ("saw", "vieron"),
    "vino": ("came", "vino"),
    "vinieron": ("came", "vinieron"),
    "dio": ("gave", "dio"),
    "dieron": ("gave", "dieron"),
    "pudo": ("could", "pudo"),
    "pudieron": ("could", "pudieron"),
    "quiso": ("wanted", "quiso"),
    "quisieron": ("wanted", "quisieron"),
    "supo": ("knew", "supo"),
    "corrió": ("ran", "corrió"),
    "cayó": ("fell", "cayó"),
    "cayeron": ("fell", "cayeron"),
    "murió": ("died", "murió"),
    "murieron": ("died", "murieron"),
    "mató": ("killed", "mató"),
    "mataron": ("killed", "mataron"),
    "luchó": ("fought", "luchó"),
    "lucharon": ("fought", "lucharon"),
    "huyó": ("fled", "huyó"),
    "huyeron": ("fled", "huyeron"),
    "gritó": ("screamed", "gritó"),
    "gritaron": ("screamed", "gritaron"),
    "susurró": ("whispered", "susurró"),
    "lloró": ("cried", "lloró"),
    "sonrió": ("smiled", "sonrió"),
    "miró": ("looked", "miró"),
    "miraron": ("looked", "miraron"),
    "habló": ("spoke", "habló"),
    "hablaron": ("spoke", "hablaron"),
    "llegó": ("arrived", "llegó"),
    "llegaron": ("arrived", "llegaron"),
    "salió": ("left", "salió"),
    "salieron": ("left", "salieron"),
    "entró": ("entered", "entró"),
    "entraron": ("entered", "entraron"),
    "tomó": ("took", "tomó"),
    "tomaron": ("took", "tomaron"),
    "dejó": ("left/let", "dejó"),
    "sintió": ("felt", "sintió"),
    "sintieron": ("felt", "sintieron"),
    "pensó": ("thought", "pensó"),
    "pensaron": ("thought", "pensaron"),
    "abrió": ("opened", "abrió"),
    "cerró": ("closed", "cerró"),
    "rompió": ("broke", "rompió"),
    "levantó": ("lifted", "levantó"),
    "levantaron": ("lifted", "levantaron"),
    "encontró": ("found", "encontró"),
    "encontraron": ("found", "encontraron"),
    "buscó": ("searched", "buscó"),
    "esperó": ("waited", "esperó"),
    "recordó": ("remembered", "recordó"),
    "prometió": ("promised", "prometió"),
    "juró": ("swore", "juró"),
    "traicionó": ("betrayed", "traicionó"),
    "decidió": ("decided", "decidió"),
    "intentó": ("tried", "intentó"),
    "logró": ("achieved", "logró"),
    "preguntó": ("asked", "preguntó"),
    "respondió": ("answered", "respondió"),
    "ordenó": ("ordered", "ordenó"),
    "siguió": ("followed", "siguió"),
    "siguieron": ("followed", "siguieron"),
    "llevó": ("carried", "llevó"),
    "llevaron": ("carried", "llevaron"),
    "trajo": ("brought", "trajo"),
    "golpeó": ("hit", "golpeó"),
    "atacó": ("attacked", "atacó"),
    "escapó": ("escaped", "escapó"),
    "despertó": ("woke", "despertó"),
    "durmió": ("slept", "durmió"),
    "bebió": ("drank", "bebió"),
    "comió": ("ate", "comió"),
    "cayó": ("fell", "cayó"),
    "subió": ("climbed/went up", "subió"),
    "bajó": ("went down", "bajó"),
    "avanzó": ("advanced", "avanzó"),
    "retrocedió": ("retreated", "retrocedió"),
    "cruzó": ("crossed", "cruzó"),
    "regresó": ("returned", "regresó"),
    "apareció": ("appeared", "apareció"),
    "desapareció": ("disappeared", "desapareció"),
    "lanzó": ("threw/launched", "lanzó"),
    "empujó": ("pushed", "empujó"),
    "agarró": ("grabbed", "agarró"),
    "soltó": ("released", "soltó"),
    "sacó": ("drew/took out", "sacó"),
    "guardó": ("kept/stored", "guardó"),
    "señaló": ("pointed", "señaló"),
    "apretó": ("squeezed/tightened", "apretó"),
    "sujetó": ("held/grabbed", "sujetó"),
    "extendió": ("extended", "extendió"),
    "dobló": ("bent/folded", "dobló"),
    "tembló": ("trembled", "tembló"),
    "temblaron": ("trembled", "temblaron"),
    "giró": ("turned", "giró"),
    "saltó": ("jumped", "saltó"),
    "corrieron": ("ran", "corrieron"),
    "se acercó": ("approached", "se acercó"),
    "se alejó": ("moved away", "se alejó"),
    "se detuvo": ("stopped", "se detuvo"),
    "se levantó": ("stood up", "se levantó"),
    "se sentó": ("sat down", "se sentó"),
    "se arrodilló": ("knelt", "se arrodilló"),
    "se inclinó": ("bowed/leaned", "se inclinó"),
    "se volvió": ("turned around", "se volvió"),

    # ── Verbos: imperfecto (acción en curso) ──────────────────────────────────
    "miraba": ("was looking", "miraba"),
    "caminaba": ("was walking", "caminaba"),
    "corría": ("was running", "corría"),
    "luchaba": ("was fighting", "luchaba"),
    "hablaba": ("was speaking", "hablaba"),
    "esperaba": ("was waiting", "esperaba"),
    "pensaba": ("was thinking", "pensaba"),
    "sentía": ("felt", "sentía"),
    "vivía": ("lived", "vivía"),
    "dormía": ("slept", "dormía"),
    "bebía": ("drank", "bebía"),
    "comía": ("ate", "comía"),
    "sonreía": ("smiled", "sonreía"),
    "temblaba": ("trembled", "temblaba"),
    "temían": ("feared", "temían"),
    "sabía": ("knew", "sabía"),
    "podía": ("could", "podía"),
    "podían": ("could", "podían"),
    "quería": ("wanted", "quería"),
    "querían": ("wanted", "querían"),
    "veía": ("saw", "veía"),
    "veían": ("saw", "veían"),
    "oía": ("heard", "oía"),
    "oían": ("heard", "oían"),
    "llevaba": ("was carrying", "llevaba"),
    "llevaban": ("were carrying", "llevaban"),
    "buscaba": ("was searching", "buscaba"),
    "buscaban": ("were searching", "buscaban"),
    "seguía": ("was following", "seguía"),
    "seguían": ("were following", "seguían"),

    # ── Verbos: infinitivos comunes ───────────────────────────────────────────
    "ser": ("to be", "ser"),
    "estar": ("to be", "estar"),
    "tener": ("to have", "tener"),
    "hacer": ("to do/make", "hacer"),
    "poder": ("to be able", "poder"),
    "querer": ("to want", "querer"),
    "saber": ("to know", "saber"),
    "ir": ("to go", "ir"),
    "venir": ("to come", "venir"),
    "ver": ("to see", "ver"),
    "hablar": ("to speak", "hablar"),
    "mirar": ("to look", "mirar"),
    "escuchar": ("to listen", "escuchar"),
    "caminar": ("to walk", "caminar"),
    "correr": ("to run", "correr"),
    "luchar": ("to fight", "luchar"),
    "morir": ("to die", "morir"),
    "matar": ("to kill", "matar"),
    "vivir": ("to live", "vivir"),
    "llegar": ("to arrive", "llegar"),
    "salir": ("to leave", "salir"),
    "entrar": ("to enter", "entrar"),
    "buscar": ("to search", "buscar"),
    "encontrar": ("to find", "encontrar"),
    "esperar": ("to wait", "esperar"),
    "recordar": ("to remember", "recordar"),
    "pensar": ("to think", "pensar"),
    "sentir": ("to feel", "sentir"),
    "amar": ("to love", "amar"),
    "odiar": ("to hate", "odiar"),
    "temer": ("to fear", "temer"),
    "huir": ("to flee", "huir"),
    "caer": ("to fall", "caer"),
    "levantar": ("to lift", "levantar"),
    "gritar": ("to scream", "gritar"),
    "susurrar": ("to whisper", "susurrar"),
    "llorar": ("to cry", "llorar"),
    "reír": ("to laugh", "reír"),
    "sonreír": ("to smile", "sonreír"),
    "tocar": ("to touch", "tocar"),
    "agarrar": ("to grab", "agarrar"),
    "golpear": ("to hit", "golpear"),
    "proteger": ("to protect", "proteger"),
    "atacar": ("to attack", "atacar"),
    "escapar": ("to escape", "escapar"),
    "seguir": ("to follow", "seguir"),
    "traer": ("to bring", "traer"),
    "llevar": ("to carry", "llevar"),
    "dejar": ("to leave/let", "dejar"),
    "tomar": ("to take", "tomar"),
    "abrir": ("to open", "abrir"),
    "cerrar": ("to close", "cerrar"),
    "romper": ("to break", "romper"),
    "quemar": ("to burn", "quemar"),
    "mover": ("to move", "mover"),
    "girar": ("to turn", "girar"),
    "dormir": ("to sleep", "dormir"),
    "comer": ("to eat", "comer"),
    "beber": ("to drink", "beber"),
    "respirar": ("to breathe", "respirar"),
    "sangrar": ("to bleed", "sangrar"),
    "sufrir": ("to suffer", "sufrir"),
    "sobrevivir": ("to survive", "sobrevivir"),
    "perder": ("to lose", "perder"),
    "ganar": ("to win", "ganar"),
    "aprender": ("to learn", "aprender"),
    "mentir": ("to lie", "mentir"),
    "jurar": ("to swear", "jurar"),
    "prometer": ("to promise", "prometer"),
    "traicionar": ("to betray", "traicionar"),
    "perdonar": ("to forgive", "perdonar"),
    "rendirse": ("to surrender", "rendirse"),
    "avanzar": ("to advance", "avanzar"),
    "retroceder": ("to retreat", "retroceder"),
    "revelar": ("to reveal", "revelar"),
    "confiar": ("to trust", "confiar"),
    "dudar": ("to doubt", "dudar"),
    "decidir": ("to decide", "decidir"),
    "elegir": ("to choose", "elegir"),
    "intentar": ("to try", "intentar"),
    "robar": ("to steal", "robar"),
    "destruir": ("to destroy", "destruir"),
    "preguntar": ("to ask", "preguntar"),
    "responder": ("to answer", "responder"),
    "ordenar": ("to order", "ordenar"),
    "obedecer": ("to obey", "obedecer"),
    "señalar": ("to point", "señalar"),
    "empujar": ("to push", "empujar"),
    "tirar": ("to throw", "tirar"),
    "atrapar": ("to catch", "atrapar"),
    "disparar": ("to shoot", "disparar"),
    "cortar": ("to cut", "cortar"),

    # ── Sustantivos: personas ─────────────────────────────────────────────────
    "hombre": ("man", "hombre"),
    "hombres": ("men", "hombres"),
    "mujer": ("woman", "mujer"),
    "mujeres": ("women", "mujeres"),
    "niño": ("boy", "niño"),
    "niños": ("boys", "niños"),
    "niña": ("girl", "niña"),
    "niñas": ("girls", "niñas"),
    "chico": ("boy", "chico"),
    "chica": ("girl", "chica"),
    "hijo": ("son", "hijo"),
    "hija": ("daughter", "hija"),
    "hijos": ("children", "hijos"),
    "padre": ("father", "padre"),
    "madre": ("mother", "madre"),
    "hermano": ("brother", "hermano"),
    "hermana": ("sister", "hermana"),
    "esposo": ("husband", "esposo"),
    "esposa": ("wife", "esposa"),
    "amigo": ("friend", "amigo"),
    "amiga": ("friend", "amiga"),
    "amigos": ("friends", "amigos"),
    "enemigo": ("enemy", "enemigo"),
    "enemigos": ("enemies", "enemigos"),
    "rey": ("king", "rey"),
    "reina": ("queen", "reina"),
    "príncipe": ("prince", "príncipe"),
    "princesa": ("princess", "princesa"),
    "caballero": ("knight", "caballero"),
    "caballeros": ("knights", "caballeros"),
    "guardia": ("guard", "guardia"),
    "guardias": ("guards", "guardias"),
    "soldado": ("soldier", "soldado"),
    "soldados": ("soldiers", "soldados"),
    "capitán": ("captain", "capitán"),
    "señor": ("lord", "señor"),
    "señora": ("lady", "señora"),
    "maestro": ("master", "maestro"),
    "esclavo": ("slave", "esclavo"),
    "esclava": ("slave", "esclava"),
    "prisionero": ("prisoner", "prisionero"),
    "traidor": ("traitor", "traidor"),
    "espía": ("spy", "espía"),
    "asesino": ("killer", "asesino"),
    "ladrón": ("thief", "ladrón"),
    "guerrero": ("warrior", "guerrero"),
    "guerreros": ("warriors", "guerreros"),
    "anciano": ("elder", "anciano"),
    "anciana": ("elder", "anciana"),
    "extraño": ("stranger", "extraño"),
    "aliado": ("ally", "aliado"),
    "aliados": ("allies", "aliados"),
    "heredero": ("heir", "heredero"),
    "mensajero": ("messenger", "mensajero"),
    "mercader": ("merchant", "mercader"),
    "monstruo": ("monster", "monstruo"),
    "fantasma": ("ghost", "fantasma"),
    "bruja": ("witch", "bruja"),
    "mago": ("wizard", "mago"),
    "hechicero": ("sorcerer", "hechicero"),

    # ── Sustantivos: cuerpo ───────────────────────────────────────────────────
    "cabello": ("hair", "cabello"),
    "pelo": ("hair", "pelo"),
    "ojos": ("eyes", "ojos"),
    "ojo": ("eye", "ojo"),
    "manos": ("hands", "manos"),
    "mano": ("hand", "mano"),
    "cara": ("face", "cara"),
    "rostro": ("face", "rostro"),
    "boca": ("mouth", "boca"),
    "labios": ("lips", "labios"),
    "labio": ("lip", "labio"),
    "nariz": ("nose", "nariz"),
    "cuello": ("neck", "cuello"),
    "hombros": ("shoulders", "hombros"),
    "hombro": ("shoulder", "hombro"),
    "brazos": ("arms", "brazos"),
    "brazo": ("arm", "brazo"),
    "piernas": ("legs", "piernas"),
    "pierna": ("leg", "pierna"),
    "pies": ("feet", "pies"),
    "pie": ("foot", "pie"),
    "pecho": ("chest", "pecho"),
    "espalda": ("back", "espalda"),
    "corazón": ("heart", "corazón"),
    "sangre": ("blood", "sangre"),
    "piel": ("skin", "piel"),
    "huesos": ("bones", "huesos"),
    "hueso": ("bone", "hueso"),
    "cabeza": ("head", "cabeza"),
    "frente": ("forehead", "frente"),
    "mejillas": ("cheeks", "mejillas"),
    "mejilla": ("cheek", "mejilla"),
    "barbilla": ("chin", "barbilla"),
    "mandíbula": ("jaw", "mandíbula"),
    "garganta": ("throat", "garganta"),
    "dedos": ("fingers", "dedos"),
    "dedo": ("finger", "dedo"),
    "puño": ("fist", "puño"),
    "rodillas": ("knees", "rodillas"),
    "rodilla": ("knee", "rodilla"),
    "tobillo": ("ankle", "tobillo"),
    "muñeca": ("wrist", "muñeca"),
    "codo": ("elbow", "codo"),
    "aliento": ("breath", "aliento"),
    "pulso": ("pulse", "pulso"),
    "cicatriz": ("scar", "cicatriz"),
    "herida": ("wound", "herida"),
    "heridas": ("wounds", "heridas"),
    "lágrimas": ("tears", "lágrimas"),
    "lágrima": ("tear", "lágrima"),
    "sudor": ("sweat", "sudor"),

    # ── Sustantivos: lugares ──────────────────────────────────────────────────
    "ciudad": ("city", "ciudad"),
    "ciudades": ("cities", "ciudades"),
    "pueblo": ("town", "pueblo"),
    "aldea": ("village", "aldea"),
    "reino": ("kingdom", "reino"),
    "reinos": ("kingdoms", "reinos"),
    "castillo": ("castle", "castillo"),
    "palacio": ("palace", "palacio"),
    "fortaleza": ("fortress", "fortaleza"),
    "torre": ("tower", "torre"),
    "muro": ("wall", "muro"),
    "muralla": ("wall", "muralla"),
    "puerta": ("door", "puerta"),
    "puertas": ("doors", "puertas"),
    "ventana": ("window", "ventana"),
    "ventanas": ("windows", "ventanas"),
    "pasillo": ("corridor", "pasillo"),
    "escalera": ("staircase", "escalera"),
    "mazmorra": ("dungeon", "mazmorra"),
    "celda": ("cell", "celda"),
    "bosque": ("forest", "bosque"),
    "bosques": ("forests", "bosques"),
    "montaña": ("mountain", "montaña"),
    "montañas": ("mountains", "montañas"),
    "río": ("river", "río"),
    "mar": ("sea", "mar"),
    "océano": ("ocean", "océano"),
    "lago": ("lake", "lago"),
    "desierto": ("desert", "desierto"),
    "campo": ("field", "campo"),
    "camino": ("path/road", "camino"),
    "sendero": ("trail", "sendero"),
    "puente": ("bridge", "puente"),
    "cueva": ("cave", "cueva"),
    "isla": ("island", "isla"),
    "orilla": ("shore", "orilla"),
    "acantilado": ("cliff", "acantilado"),
    "colina": ("hill", "colina"),
    "valle": ("valley", "valle"),
    "ruinas": ("ruins", "ruinas"),
    "tumba": ("tomb", "tumba"),
    "mercado": ("market", "mercado"),
    "taberna": ("tavern", "taberna"),
    "posada": ("inn", "posada"),
    "establo": ("stable", "establo"),
    "puerto": ("harbor", "puerto"),
    "jardín": ("garden", "jardín"),
    "sala": ("hall", "sala"),
    "trono": ("throne", "trono"),
    "cámara": ("chamber", "cámara"),

    # ── Sustantivos: objetos ──────────────────────────────────────────────────
    "espada": ("sword", "espada"),
    "espadas": ("swords", "espadas"),
    "daga": ("dagger", "daga"),
    "cuchillo": ("knife", "cuchillo"),
    "lanza": ("spear", "lanza"),
    "arco": ("bow", "arco"),
    "flecha": ("arrow", "flecha"),
    "flechas": ("arrows", "flechas"),
    "escudo": ("shield", "escudo"),
    "armadura": ("armor", "armadura"),
    "casco": ("helmet", "casco"),
    "hacha": ("axe", "hacha"),
    "arma": ("weapon", "arma"),
    "armas": ("weapons", "armas"),
    "corona": ("crown", "corona"),
    "anillo": ("ring", "anillo"),
    "collar": ("necklace", "collar"),
    "capa": ("cloak", "capa"),
    "manto": ("cloak", "manto"),
    "vestido": ("dress", "vestido"),
    "guantes": ("gloves", "guantes"),
    "botas": ("boots", "botas"),
    "bota": ("boot", "bota"),
    "bolsa": ("bag", "bolsa"),
    "mapa": ("map", "mapa"),
    "libro": ("book", "libro"),
    "libros": ("books", "libros"),
    "pergamino": ("scroll", "pergamino"),
    "llave": ("key", "llave"),
    "cadena": ("chain", "cadena"),
    "cuerda": ("rope", "cuerda"),
    "antorcha": ("torch", "antorcha"),
    "vela": ("candle", "vela"),
    "veneno": ("poison", "veneno"),
    "tesoro": ("treasure", "tesoro"),
    "oro": ("gold", "oro"),
    "plata": ("silver", "plata"),
    "piedra": ("stone", "piedra"),
    "piedras": ("stones", "piedras"),
    "fuego": ("fire", "fuego"),
    "llama": ("flame", "llama"),
    "llamas": ("flames", "llamas"),
    "ceniza": ("ash", "ceniza"),
    "cenizas": ("ashes", "cenizas"),
    "carta": ("letter", "carta"),
    "cartas": ("letters", "cartas"),
    "bandera": ("banner", "bandera"),
    "cofre": ("chest", "cofre"),
    "jaula": ("cage", "jaula"),
    "escudo": ("shield", "escudo"),

    # ── Sustantivos: naturaleza ───────────────────────────────────────────────
    "cielo": ("sky", "cielo"),
    "sol": ("sun", "sol"),
    "luna": ("moon", "luna"),
    "estrellas": ("stars", "estrellas"),
    "estrella": ("star", "estrella"),
    "viento": ("wind", "viento"),
    "lluvia": ("rain", "lluvia"),
    "nieve": ("snow", "nieve"),
    "tormenta": ("storm", "tormenta"),
    "niebla": ("mist", "niebla"),
    "sombra": ("shadow", "sombra"),
    "sombras": ("shadows", "sombras"),
    "oscuridad": ("darkness", "oscuridad"),
    "luz": ("light", "luz"),
    "amanecer": ("dawn", "amanecer"),
    "anochecer": ("dusk", "anochecer"),
    "noche": ("night", "noche"),
    "día": ("day", "día"),
    "árbol": ("tree", "árbol"),
    "árboles": ("trees", "árboles"),
    "agua": ("water", "agua"),
    "tierra": ("earth/land", "tierra"),
    "roca": ("rock", "roca"),
    "barro": ("mud", "barro"),
    "arena": ("sand", "arena"),
    "humo": ("smoke", "humo"),
    "hielo": ("ice", "hielo"),
    "polvo": ("dust", "polvo"),
    "olas": ("waves", "olas"),
    "trueno": ("thunder", "trueno"),
    "relámpago": ("lightning", "relámpago"),
    "brisa": ("breeze", "brisa"),

    # ── Sustantivos: emociones y abstractos ───────────────────────────────────
    "miedo": ("fear", "miedo"),
    "dolor": ("pain", "dolor"),
    "amor": ("love", "amor"),
    "odio": ("hate", "odio"),
    "esperanza": ("hope", "esperanza"),
    "desesperación": ("despair", "desesperación"),
    "rabia": ("rage", "rabia"),
    "ira": ("anger", "ira"),
    "alegría": ("joy", "alegría"),
    "tristeza": ("sadness", "tristeza"),
    "soledad": ("loneliness", "soledad"),
    "orgullo": ("pride", "orgullo"),
    "vergüenza": ("shame", "vergüenza"),
    "culpa": ("guilt", "culpa"),
    "furia": ("fury", "furia"),
    "valor": ("courage", "valor"),
    "cobardía": ("cowardice", "cobardía"),
    "lealtad": ("loyalty", "lealtad"),
    "traición": ("betrayal", "traición"),
    "venganza": ("revenge", "venganza"),
    "fuerza": ("strength", "fuerza"),
    "debilidad": ("weakness", "debilidad"),
    "libertad": ("freedom", "libertad"),
    "destino": ("fate", "destino"),
    "muerte": ("death", "muerte"),
    "vida": ("life", "vida"),
    "verdad": ("truth", "verdad"),
    "mentira": ("lie", "mentira"),
    "secreto": ("secret", "secreto"),
    "misterio": ("mystery", "misterio"),
    "silencio": ("silence", "silencio"),
    "peligro": ("danger", "peligro"),
    "guerra": ("war", "guerra"),
    "batalla": ("battle", "batalla"),
    "batallas": ("battles", "batallas"),
    "paz": ("peace", "paz"),
    "victoria": ("victory", "victoria"),
    "derrota": ("defeat", "derrota"),
    "honor": ("honor", "honor"),
    "gloria": ("glory", "gloria"),
    "sacrificio": ("sacrifice", "sacrificio"),
    "promesa": ("promise", "promesa"),
    "juramento": ("oath", "juramento"),
    "sueño": ("dream", "sueño"),
    "pesadilla": ("nightmare", "pesadilla"),
    "recuerdos": ("memories", "recuerdos"),
    "recuerdo": ("memory", "recuerdo"),
    "magia": ("magic", "magia"),
    "maldición": ("curse", "maldición"),
    "profecía": ("prophecy", "profecía"),
    "leyenda": ("legend", "leyenda"),
    "caos": ("chaos", "caos"),
    "justicia": ("justice", "justicia"),
    "sabiduría": ("wisdom", "sabiduría"),
    "conocimiento": ("knowledge", "conocimiento"),
    "poder": ("power", "poder"),

    # ── Sustantivos: tiempo ───────────────────────────────────────────────────
    "años": ("years", "años"),
    "año": ("year", "año"),
    "meses": ("months", "meses"),
    "mes": ("month", "mes"),
    "semanas": ("weeks", "semanas"),
    "semana": ("week", "semana"),
    "horas": ("hours", "horas"),
    "hora": ("hour", "hora"),
    "momento": ("moment", "momento"),
    "momentos": ("moments", "momentos"),
    "mañana": ("morning", "mañana"),
    "tarde": ("afternoon", "tarde"),
    "medianoche": ("midnight", "medianoche"),
    "mediodía": ("noon", "mediodía"),
    "invierno": ("winter", "invierno"),
    "verano": ("summer", "verano"),
    "primavera": ("spring", "primavera"),
    "otoño": ("autumn", "otoño"),
    "siglo": ("century", "siglo"),
    "eternidad": ("eternity", "eternidad"),

    # ── Animales ──────────────────────────────────────────────────────────────
    "caballos": ("horses", "caballos"),
    "caballo": ("horse", "caballo"),
    "lobos": ("wolves", "lobos"),
    "lobo": ("wolf", "lobo"),
    "dragones": ("dragons", "dragones"),
    "dragón": ("dragon", "dragón"),
    "cuervos": ("ravens", "cuervos"),
    "cuervo": ("raven", "cuervo"),
    "serpiente": ("snake", "serpiente"),
    "serpientes": ("snakes", "serpientes"),
    "perros": ("dogs", "perros"),
    "perro": ("dog", "perro"),
    "gato": ("cat", "gato"),
    "oso": ("bear", "oso"),
    "águila": ("eagle", "águila"),
    "zorro": ("fox", "zorro"),
    "ciervo": ("stag", "ciervo"),
    "halcón": ("hawk", "halcón"),
    "araña": ("spider", "araña"),
    "ratas": ("rats", "ratas"),
    "rata": ("rat", "rata"),

    # ── Adjetivos: físicos ────────────────────────────────────────────────────
    "alto": ("tall", "alto"),
    "alta": ("tall", "alta"),
    "bajo": ("short", "bajo"),
    "baja": ("short", "baja"),
    "grande": ("big", "grande"),
    "pequeño": ("small", "pequeño"),
    "pequeña": ("small", "pequeña"),
    "joven": ("young", "joven"),
    "viejo": ("old", "viejo"),
    "vieja": ("old", "vieja"),
    "delgado": ("slim", "delgado"),
    "delgada": ("slim", "delgada"),
    "fuerte": ("strong", "fuerte"),
    "débil": ("weak", "débil"),
    "rápido": ("fast", "rápido"),
    "rápida": ("fast", "rápida"),
    "lento": ("slow", "lento"),
    "lenta": ("slow", "lenta"),
    "oscuro": ("dark", "oscuro"),
    "oscura": ("dark", "oscura"),
    "pálido": ("pale", "pálido"),
    "pálida": ("pale", "pálida"),
    "rojo": ("red", "rojo"),
    "roja": ("red", "roja"),
    "negro": ("black", "negro"),
    "negra": ("black", "negra"),
    "blanco": ("white", "blanco"),
    "blanca": ("white", "blanca"),
    "dorado": ("golden", "dorado"),
    "dorada": ("golden", "dorada"),
    "plateado": ("silver", "plateado"),
    "gris": ("grey", "gris"),
    "verde": ("green", "verde"),
    "azul": ("blue", "azul"),
    "frío": ("cold", "frío"),
    "fría": ("cold", "fría"),
    "caliente": ("hot", "caliente"),
    "duro": ("hard", "duro"),
    "dura": ("hard", "dura"),
    "suave": ("soft", "suave"),
    "afilado": ("sharp", "afilado"),
    "pesado": ("heavy", "pesado"),
    "vivo": ("alive", "vivo"),
    "viva": ("alive", "viva"),
    "muerto": ("dead", "muerto"),
    "muerta": ("dead", "muerta"),
    "herido": ("wounded", "herido"),
    "herida": ("wounded", "herida"),
    "roto": ("broken", "roto"),
    "rota": ("broken", "rota"),
    "antiguo": ("ancient", "antiguo"),
    "antigua": ("ancient", "antigua"),
    "nuevo": ("new", "nuevo"),
    "nueva": ("new", "nueva"),
    "oculto": ("hidden", "oculto"),
    "oculta": ("hidden", "oculta"),
    "enorme": ("huge", "enorme"),
    "salvaje": ("wild", "salvaje"),
    "vacío": ("empty", "vacío"),
    "vacía": ("empty", "vacía"),
    "lleno": ("full", "lleno"),
    "llena": ("full", "llena"),
    "sucio": ("dirty", "sucio"),
    "sucia": ("dirty", "sucia"),
    "limpio": ("clean", "limpio"),
    "profundo": ("deep", "profundo"),
    "profunda": ("deep", "profunda"),
    "plateada": ("silver", "plateada"),
    "rubio": ("blond", "rubio"),
    "rubia": ("blond", "rubia"),

    # ── Adjetivos: carácter ───────────────────────────────────────────────────
    "valiente": ("brave", "valiente"),
    "cobarde": ("cowardly", "cobarde"),
    "cruel": ("cruel", "cruel"),
    "amable": ("kind", "amable"),
    "sabio": ("wise", "sabio"),
    "leal": ("loyal", "leal"),
    "honesto": ("honest", "honesto"),
    "orgulloso": ("proud", "orgulloso"),
    "orgullosa": ("proud", "orgullosa"),
    "humilde": ("humble", "humilde"),
    "arrogante": ("arrogant", "arrogante"),
    "astuto": ("cunning", "astuto"),
    "astuta": ("cunning", "astuta"),
    "inocente": ("innocent", "inocente"),
    "culpable": ("guilty", "culpable"),
    "peligroso": ("dangerous", "peligroso"),
    "peligrosa": ("dangerous", "peligrosa"),
    "misterioso": ("mysterious", "misterioso"),
    "desesperado": ("desperate", "desesperado"),
    "desesperada": ("desperate", "desesperada"),
    "furioso": ("furious", "furioso"),
    "furiosa": ("furious", "furiosa"),
    "tranquilo": ("calm", "tranquilo"),
    "tranquila": ("calm", "tranquila"),
    "silencioso": ("silent", "silencioso"),
    "silenciosa": ("silent", "silenciosa"),
    "seguro": ("safe", "seguro"),
    "segura": ("safe", "segura"),
    "libre": ("free", "libre"),
    "muerto": ("dead", "muerto"),
    "vivo": ("alive", "vivo"),

    # ── Adverbios ─────────────────────────────────────────────────────────────
    "siempre": ("always", "siempre"),
    "nunca": ("never", "nunca"),
    "jamás": ("never", "jamás"),
    "quizás": ("perhaps", "quizás"),
    "pronto": ("soon", "pronto"),
    "solo": ("alone", "solo"),
    "sola": ("alone", "sola"),
    "juntos": ("together", "juntos"),
    "lejos": ("far", "lejos"),
    "cerca": ("near", "cerca"),
    "arriba": ("above", "arriba"),
    "abajo": ("below", "abajo"),
    "adelante": ("forward", "adelante"),
    "dentro": ("inside", "dentro"),
    "fuera": ("outside", "fuera"),
    "despacio": ("slowly", "despacio"),
    "rápidamente": ("quickly", "rápidamente"),
    "suavemente": ("softly", "suavemente"),
    "finalmente": ("finally", "finalmente"),
}

# ──────────────────────────────────────────────────────────────────────────────
# Preprocesamiento: ordenar entradas de más larga a más corta
# ──────────────────────────────────────────────────────────────────────────────
ENTRADAS_ORDENADAS: list[tuple[str, str, str]] = sorted(
    [(esp, en, glosa) for esp, (en, glosa) in ES_EN.items()],
    key=lambda x: -len(x[0])
)

# Caché de patrones compilados
_CACHE: dict[str, re.Pattern] = {}

def patron_de(palabra: str) -> re.Pattern:
    if palabra not in _CACHE:
        # (?<!\w) y (?!\w) para límites de palabra que soporten tildes
        _CACHE[palabra] = re.compile(
            r'(?<!\w)' + re.escape(palabra) + r'(?!\w)',
            re.IGNORECASE
        )
    return _CACHE[palabra]


# ──────────────────────────────────────────────────────────────────────────────
# Motor de anotación
# ──────────────────────────────────────────────────────────────────────────────

def anotar_texto(texto: str, intensidad: int) -> str:
    """
    Reemplaza palabras españolas por '<mark>english</mark>'.
    - intensidad: máximo de palabras DISTINTAS a reemplazar por fragmento.
    - Preserva mayúsculas del token original.
    - No toca el interior de reemplazos ya hechos.
    """
    if not texto.strip():
        return texto

    texto_trabajo = texto
    reemplazos_count = 0

    # Mezclar para variar el vocabulario mostrado en cada fragmento
    entradas = list(ENTRADAS_ORDENADAS)
    random.shuffle(entradas)

    for esp, en, glosa in entradas:
        if intensidad > 0 and reemplazos_count >= intensidad:
            break

        patron = patron_de(esp)
        nueva_cadena = []
        ultimo = 0
        hubo = False

        for m in patron.finditer(texto_trabajo):
            ini, fin = m.start(), m.end()

            # No reemplazar dentro de etiquetas <mark> ya anotadas
            antes = texto_trabajo[:ini]
            if antes.count('<mark>') > antes.count('</mark>'):
                continue

            token_orig = m.group(0)
            # Preservar mayúscula inicial
            if token_orig[0].isupper():
                en_disp = en[0].upper() + en[1:]
            else:
                en_disp = en

            nueva_cadena.append(texto_trabajo[ultimo:ini])
            nueva_cadena.append(f"<mark>{en_disp}</mark>")
            ultimo = fin
            hubo = True

        if hubo:
            nueva_cadena.append(texto_trabajo[ultimo:])
            texto_trabajo = "".join(nueva_cadena)
            reemplazos_count += 1

    return texto_trabajo


def procesar_nodo(nodo: NavigableString, intensidad: int) -> None:
    if isinstance(nodo, NavigableString) and nodo.parent.name not in (
        'script', 'style', 'code', 'pre', 'mark'
    ):
        texto = str(nodo)
        nuevo = anotar_texto(texto, intensidad)
        if nuevo != texto:
            # Necesitamos insertar HTML real (<mark>), no texto plano
            fragmento = BeautifulSoup(nuevo, 'html.parser')
            nodo.replace_with(fragmento)


def procesar_html(contenido_html: bytes, intensidad: int) -> bytes:
    sopa = BeautifulSoup(contenido_html, 'html.parser')
    for nodo in list(sopa.find_all(string=True)):
        procesar_nodo(nodo, intensidad)
    return str(sopa).encode('utf-8')


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────────────────────────────────────

def procesar_epub(ruta_entrada: str, ruta_salida: str, intensidad: int = 3):
    print(f"\n📖 Cargando: {ruta_entrada}")
    libro = epub.read_epub(ruta_entrada)

    print(f"✏️  Anotando ({len(ES_EN)} entradas en diccionario, intensidad={intensidad})…")
    items_procesados = 0
    for item in libro.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        contenido_anotado = procesar_html(item.get_content(), intensidad)
        item.set_content(contenido_anotado)
        items_procesados += 1

    print(f"   Capítulos/secciones procesados: {items_procesados}")
    print(f"💾 Guardando: {ruta_salida}")
    epub.write_epub(ruta_salida, libro)

    ruta_dict = Path(ruta_salida).with_suffix('.json')
    with open(ruta_dict, 'w', encoding='utf-8') as f:
        json.dump(
            {esp: en for esp, (en, _) in ES_EN.items()},
            f, ensure_ascii=False, indent=2
        )
    print(f"   Diccionario guardado en: {ruta_dict}")
    print("\n✅ ¡Listo! Abre el epub anotado en tu lector favorito.\n")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Inserta vocabulario en inglés en un epub en español para aprendizaje."
    )
    parser.add_argument("epub", help="Ruta al archivo .epub de entrada")
    parser.add_argument("--salida", "-s", default=None,
                        help="Ruta del epub de salida (default: <nombre>_anotado.epub)")
    parser.add_argument(
        "--intensidad", "-i", type=int, default=3,
        help="Palabras distintas a reemplazar por fragmento de texto (default=3, más alto = más denso)"
    )
    args = parser.parse_args()

    ruta_entrada = Path(args.epub)
    if not ruta_entrada.exists():
        print(f"❌ No se encontró el archivo: {ruta_entrada}")
        return

    ruta_salida = args.salida or str(
        ruta_entrada.with_stem(ruta_entrada.stem + "_anotado")
    )
    procesar_epub(str(ruta_entrada), ruta_salida, intensidad=args.intensidad)


if __name__ == "__main__":
    main()