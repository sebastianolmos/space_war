from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import sys

import transformations as tr
import easy_shaders as es
import scene_graph as sg
import animation as anim
import collisions as cl
import math
import random

#Dimensiones de la pantalla que se inician más adelante
WIDTH = 0
HEIGHT = 0

NEBULA_LOADED = 3 #Numero de nebulosas cargadas en cada momento de ejecucion
STARS_LOADED = 12 #numero de pauqetes de estrellas cargadas
PLANETS_LOADED = 5 #numero de planetas cargados

NEBULA_SPEED = 0.05 #velocidad de las nebulosas
NEBULA_MIN_SCALE = 1 #tamaño minimo que puede tener una nebulosa
NEBULA_MAX_SCALE = 3 #tamaño maximo que puede tener una nebulosa

STAR_POSY = 0.2 #distancia vertical entre los paquetes de estrellas
STAR_DELTA_POSY = 0.03  #variacion en la posixion vertical que puede tener cada estrella con respecto a su paquete
STARS_IN_X_MIN = 3 #cantidad minima de estrellas que puede tener un paquete
STARS_IN_X_MAX = 6 #cantidad maxima de estrellas que puede tener un paquete
STAR_MIN_SIZE = 0.03 #tamaño minimo que puede tener una estrella
STAR_MAX_SIZE = 0.12 #tamaño maximo que puede tener una estrella
STAR_MIN_FPS = 2 #velocidad de animacion minima que puede tener una estrella
STAR_MAX_FPS = 8 #velocidad de animacion maxima que puede tener una estrella
STARS_SPEED = 0.1  #velocidad de las estrellas

PLANET_MIN_POSY = 0.8 #ditancia minima entre planetas
PLANET_MAX_POSY = 1.2 #ditancia maxima entre planetas
PLANET_MIN_SIZE = 0.3 #tamaño minimo que puede tener un planeta
PLANET_MAX_SIZE = 0.8 #tamaño maximo que puede tener un planeta
PLANET_SPEED = 0.2 #velocidad de los planetas

#variables que contendran las gpuSHapes/texturas de las nebulas, estrellas (animaciones en este caso) y planetas respectivamente
nebulae_images = list()
stars_images = list()
planets_images = list()

#Se crea la clase gameObject que se hereda de la clase nodo, incluye parametros basicos que ocupa un elemento en el juego
class gameObject(sg.SceneGraphNode):
    def __init__(self, name):
        sg.SceneGraphNode.__init__(self, name)
        self.position = np.zeros(3)
        self.velocity = np.zeros(3)
        self.size = 0
        self.time_counter = 0

#clase de la bala, hererada de gameobject icluyendo parametros de la bala.
class bulletObject(gameObject):
    def __init__(self, name):
        gameObject.__init__(self, name)
        self.fromEnemy = True
        self.toDelete=False
        self.isExploding = False

#funcion que realiza una interpolacion lineal
def lerp(A, B, C):
    value = (C * A) + ((1 - C) * B)
    return value

#se cargan las dimensiones de la ventana
def setupWindowSize(width, height):
    global WIDTH, HEIGHT
    WIDTH = width
    HEIGHT = height

#funcion que incializa las nebulosas
def setupNebulae(image, main_node):
    global nebulae_images
    #se crean las gpushapes de cada nebulosa y la coleccion de nebulosas
    nebulae_images = anim.createFrames(image, [460, 460], [0, 0], [3], [0, 0])
    nebula_collection = sg.SceneGraphNode("nebulae")
    #se agrega la coleccion de nebulosas al nodo principal
    main_node.childs += [nebula_collection]

    #referencia a la coleccion de nebulosas
    Nebulae = findNode(main_node, "nebulae")
    for i in range(NEBULA_LOADED):
        AddNebulae(Nebulae)
        #se agregan las primeras nebulosas

    #se entrega la referencia a la coleccion
    return Nebulae

#funcion que incializa las estrellas
def setupStars(image, main_node):
    global stars_images
    # se crean las animaciones de cada estrella y la coleccion de estrellas se agrega al nodo principal
    for i in range(16):
        stars_images += [anim.createFrames(image, [11, 11], [0, 0], [10], [0, i])]
    stars_collection = sg.SceneGraphNode("stars")
    main_node.childs += [stars_collection]

    Stars = findNode(main_node, "stars")
    #se añaden las primeras estrellas
    for j in range(STARS_LOADED):
        addStars(Stars)
    #se entrega la referencia a la coleccion
    return Stars

#funcion que incializa los planetas
def setupPlanets(image, main_node):
    global planets_images
    # se crean las gpushapes de cada planeta y la coleccion de planetas
    planets_images = anim.createFrames(image, [64, 64], [0, 0], [3, 4], [0, 0])
    planets_collection = sg.SceneGraphNode("planets")
    #se agrega la coleccion de planetas al nodo principal
    main_node.childs += [planets_collection]

    # referencia a la coleccion de planetas
    Planets = findNode(main_node, "planets")
    #se agregan los primeros planetas
    for p in range(PLANETS_LOADED):
        addPlanet(Planets)
        #se retorna la referencia a la coleccion
    return Planets

#funcion que actualiza la posicion de las nebulosas
def updateNebulae(delta_time, neb_collection):
    last_neb_pos = neb_collection.childs[0].position[1]
    last_neb_size = neb_collection.childs[0].size
    #si la nebulosa mas lejana sale de la pantalla, se elimina y se agrega otra
    if last_neb_pos < -1 - last_neb_size:
        del(neb_collection.childs[0])
        AddNebulae(neb_collection)

    #se mueve cada nebulosa segun su velocidad
    for neb in neb_collection.childs:
        neb.position[0] = neb.transform[0][3]
        neb.position[1] = neb.transform[1][3]
        neb.position[2] = neb.transform[2][3]

        vx = neb.position[0]
        vy = neb.position[1] - NEBULA_SPEED * delta_time * WIDTH / HEIGHT
        vz = neb.position[2]
        neb.transform = tr.translate(vx, vy, vz)

#funcion que actualiza la posicion de las estrellas
def updateStars(delta_time, stars_coll):
    last_stars_node_pos = stars_coll.childs[0].position[1]
    #si las estrellas mas lejanas salen de la pantalla, se eliminan y se agrega otro paquete de estrellas
    if last_stars_node_pos < -1.1:
        del(stars_coll.childs[0])
        addStars(stars_coll)

    #se mueve cada estrella segun su velocidad
    for starNode in stars_coll.childs:
        starNode.position[0] = starNode.transform[0][3]
        starNode.position[1] = starNode.transform[1][3]
        starNode.position[2] = starNode.transform[2][3]

        vx = starNode.position[0]
        vy = starNode.position[1] - STARS_SPEED * delta_time * WIDTH / HEIGHT
        vz = starNode.position[2]
        starNode.transform = tr.translate(vx, vy, vz)

#funcion que actualiza la posicion de los planetas
def updatePlanets(delta_time, planet_coll):
    last_planet_pos = planet_coll.childs[0].position[1]
    # si el planeta mas lejano sale de la pantalla, se elimina y se agrega otro
    if last_planet_pos < -1.2:
        del(planet_coll.childs[0])
        addPlanet(planet_coll)

    #se mueven los planetas segun su velocidad
    for planet in planet_coll.childs:
        planet.position[0] = planet.transform[0][3]
        planet.position[1] = planet.transform[1][3]
        planet.position[2] = planet.transform[2][3]

        vx = planet.position[0]
        vy = planet.position[1] - planet.velocity[1] * delta_time * WIDTH / HEIGHT
        vz = planet.position[2]
        planet.transform = tr.translate(vx, vy, vz)

#version modificada de drawSceneGraphNode() para dibujar las texturas y dibujar las animaciones
def drawSceneGame(node, pipeline, transformName, delta_time, isPaused,  parentTransform=tr.identity()):
    assert(isinstance(node, sg.SceneGraphNode))

    newTransform = np.matmul(parentTransform, node.transform)

    #se ha encontrado una animacion para dibujar
    if len(node.childs) == 1 and isinstance(node.childs[0], anim.Anim_Controller):

        node.childs[0].Update(pipeline, delta_time, newTransform, isPaused)

    #las hitboxes no se dibujan con este pipeline
    elif isinstance(node, cl.CollisionShape):
        return

    #si se encuentra una textura la dibuja
    elif len(node.childs) == 1  and isinstance(node.childs[0], es.GPUShape):
        leaf = node.childs[0]
        glUniformMatrix4fv(glGetUniformLocation(pipeline.shaderProgram, transformName), 1, GL_TRUE, newTransform)
        pipeline.drawShape(leaf)

    else:
        for child in node.childs:
            drawSceneGame(child, pipeline, transformName, delta_time, isPaused, newTransform )

#version modificada de drawSceneGraphNode() para dibujar las hitboxes
def drawCollisionShapes(node, pipeline, transformName, parentTransform=tr.identity()):
    assert(isinstance(node, sg.SceneGraphNode))

    newTransform = np.matmul(parentTransform, node.transform)

    #si se encuentra una animacion o un gameObject sin hitboxes no las dibuja
    if len(node.childs) == 1 and isinstance(node.childs[0], anim.Anim_Controller):
        return
    elif len(node.childs) == 1 and isinstance(node, gameObject):
        return

    #si encuentra un gameObject con hitbox, la dibuja
    elif len(node.childs) == 2 and isinstance(node, gameObject):
        drawCollisionShapes(node.childs[1], pipeline, transformName,  newTransform)

    elif len(node.childs) == 1  and isinstance(node.childs[0], es.GPUShape):
        leaf = node.childs[0]
        glUniformMatrix4fv(glGetUniformLocation(pipeline.shaderProgram, transformName), 1, GL_TRUE, newTransform)
        pipeline.drawShape(leaf)

    else:
        for child in node.childs:
            drawCollisionShapes(child, pipeline, transformName,  newTransform)

#version modificada de la funcion findNode() para que funcione en un grafo de escena con hojas que son gpushapes y anim_controllers
def findNode(node, name):
    # The name was not found in this path
    if isinstance(node, es.GPUShape) or isinstance(node, anim.Anim_Controller):
        return None

    # This is the requested node
    if node.name == name:
        return node

    # All childs are checked for the requested name
    for child in node.childs:
        foundNode = findNode(child, name)
        if foundNode != None:
            return foundNode

    # No child of this node had the requested name
    return None

#funcion que agrega una nebula random con parametros aleatorios
def AddNebulae(neb_collection):
    #se define un tamaño random
    scale = NEBULA_MIN_SCALE + random.random() * (NEBULA_MAX_SCALE - NEBULA_MIN_SCALE)
    size = scale
    #se define una rotacion random
    randRotInt = random.randint(0, 3)
    rotation =  randRotInt * math.pi/2
    #posicion horizontal random
    posX = random.randint(-1,1) * random.random() * scale* 0.5
    #posicion vertical definida por las otras nebulosas
    posY = 0
    if len(neb_collection.childs) == 0:
        posY = -1 + size/2
    else:
        last_posY = neb_collection.childs[-1].position[1]
        last_size = neb_collection.childs[-1].size
        posY = last_posY + last_size/2 + size/2

    #se crea un nodo que contiene una nebula random y se escal
    nebula =  sg.SceneGraphNode("nebula")
    nebula.transform = tr.matmul([tr.uniformScale(scale)])
    rand_nebula = random.randint(0, len(nebulae_images)-1)
    nebula.childs += [nebulae_images[rand_nebula]]

    #nodo que se rota
    scaledNebula = sg.SceneGraphNode("scaledNebula")
    scaledNebula.transform = tr.rotationZ(rotation)
    scaledNebula.childs += [nebula]

    #gameObject que se posiciona en la pantalla
    neb_object = gameObject("neb_object")
    neb_object.transform = tr.translate(posX, posY, 0)
    neb_object.size =size
    neb_object.position[0] = posX
    neb_object.position[1] = posY
    neb_object.childs += [scaledNebula]

    #se agrega a la coleccion de nodos
    neb_collection.childs += [neb_object]

#funcion que agrega un paquete de estrellas random con parametros aleatorios
def addStars(stars_coll):
    posY = 0
    #posicion horizontal del paquete depende de los anteriores
    if len(stars_coll.childs) == 0:
        posY = -1
    else:
        posY = stars_coll.childs[-1].position[1] + STAR_POSY

    #se crea un gameObject que vendria siendo el paquete de estrellas y se posiciona
    start_node = gameObject("star_node")
    start_node.transform = tr.translate(0, posY, 0)
    start_node.position[1] = posY
    #cantidad random de estrellas que contendra el paquete
    amountInX = random.randint(STARS_IN_X_MIN, STARS_IN_X_MAX)

    for x in range(amountInX):
        #por cada estrella del paquete se crea una animController con una estrella random, tamaño random y se inicializa
        anim0 = anim.Animation(stars_images[random.randint(0, 15)], random.randint(STAR_MIN_FPS, STAR_MAX_FPS), True, False)
        scale = STAR_MIN_SIZE + random.random() * (STAR_MAX_SIZE - STAR_MIN_SIZE)
        anim_Ctl = anim.Anim_Controller({"star" : anim0}, [scale, scale * WIDTH/HEIGHT, scale], 0)
        anim_Ctl.Play("star")

        #posicion horizontal random
        startPosX = -1 +(2/amountInX) * x + random.random()* (2/amountInX)
        #posicion vertical variando un poco con respecto a la del paquete
        startPosY = (-1 + random.random() * 2) * STAR_DELTA_POSY

        #se crea el gameobject de cada estrella con su animacion
        star_object = gameObject("star")
        star_object.transform = tr.translate(startPosX, startPosY, 0)
        star_object.position = np.array([startPosX, startPosY, 0])
        star_object.childs += [anim_Ctl]
        #se agrega cada estrella al paquete
        start_node.childs += [star_object]
    #se agrega el paquete a la coleccion de estrellas
    stars_coll.childs += [start_node]

#funcion que agrega un planeta random con parametros aleatorios
def addPlanet(planets_coll):
    # posicion vertical definida por los otros planetas
    posY = 0
    if len(planets_coll.childs) == 0:
        posY = -1
    else:
        posY = planets_coll.childs[-1].position[1] + posY
    #Posicion  random del planeta
    planet_posX = -1 + random.random() * 2
    planet_posY = posY + PLANET_MIN_POSY + random.random() * (PLANET_MAX_POSY - PLANET_MIN_POSY)
    planet_velY = PLANET_SPEED
    planet_index = random.randint(0, len(planets_images)-1) #se le entrega la textura
    # se define un tamaño random
    planet_scale = PLANET_MIN_SIZE + random.random() * (PLANET_MAX_SIZE - PLANET_MIN_SIZE)

    #se crean un nodo donde se escala
    planet_object = sg.SceneGraphNode("planet_object")
    planet_object.transform = tr.scale(planet_scale, WIDTH/HEIGHT * planet_scale, planet_scale)
    planet_object.childs += [planets_images[planet_index]]
    #se crea un gameobject con el que se posisiona el planeta
    planet = gameObject("planet")
    planet.transform = tr.translate(planet_posX, planet_posY, 0)
    planet.position = np.array([planet_posX, planet_posY, 0])
    planet.velocity = np.array([0, planet_velY, 0])
    planet.childs += [planet_object]

    #se agrega a la coleccion de planetas
    planets_coll.childs += [planet]