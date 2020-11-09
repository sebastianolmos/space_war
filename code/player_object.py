from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import sys

import transformations as tr
import easy_shaders as es
import basic_shapes as bs
import scene_graph as sg
import animation as anim
import game_object as go
import collisions as cl
import enemies as en
import math
import random

#Se definen valores de parametros del Player
PLAYER_ACC = 0.01 #magnitud de la aceleracion con que se mueve
PLAYER_MAX_SPEED = 0.7 #magnitud de la máxima velocidad que puede alcanzar la nave
PLAYER_FRICC = 0.985 #valor para desacelerar la nave cuando no recibe input
PLAYER_SIZE = 0.5 #escala de la nave
BULLET_SPEED = 1.5 #velocidad de la bala disparada por el jugador
PLAYER_HITBOX_RADIO = 0.08 #Radio de la hitbox de Player
BULLET_HITBOX_RADIO = 0.03 #Radio de la hitbox de la bala disparada por la nave
BULLET_RELOAD_TIME = 0.4 #tiempo de recarga, en el que no se puede disparar volver a disparar
HURTED_TIME = 1.5 #tiempo en el que el player una vez herido, no puede ser herido denuevo
PLAYER_LEAVE_SPEED = 0.1 #Velocidad con el que la nave deja la pantalla cuando el usuaria gana

#Se definen valores de parametros de la UI: vida de la nave como corazones
HEART_SIZE = 1 #escala de cada corazon
HEART1_POSX = -0.9 #posicion vertical  del primer corazon
HEARTS_POSY = -0.9 #posicion horizontal de los corazones
HEARTS_LENGTH = 0.3 #largo en el que se distribuyen los corazones

#Dimensiones de la pantalla que se inician más adelante
WIDTH = 0
HEIGHT = 0

#contador de las balas de player
player_bullet_counter = 0

#clase para manejar el input del usuario
class Controller:
    def __init__(self):
        self.is_up_pressed = False
        self.is_down_pressed = False
        self.is_left_pressed = False
        self.is_right_pressed = False
        self.is_space_press = False
        self.collisionShapeView = False
        self.isPaused = False

#clase para el objeto Player que herda la clase gameObject
class playerObject(go.gameObject):
    def __init__(self, name):
        go.gameObject.__init__(self, name)
        self.health = 3 #vida del player
        self.bullet = None #referencia a la bala a disparar (gpuShape)
        self.bullet_pos = np.array([0, 0.06, 0]) #posicion de donde sale la bal, respecto del player
        self.bullet_size = 0.5 #escala de la bala
        self.isHurted = False #bool que indica si el player esta herido
        self.isExploding = False #bool que indica si el player esta explotando despues de perder las vidas
        self.isDead = False #bool que indica si el player esta muerto
        self.time_counter2 = BULLET_RELOAD_TIME + 1 #contador de tiempo utilizado para el tiempo de recarga de la bala

    #funcion para disparar una bala
    def shoot(self, bullet_collection, counter):
        #se crea un nodo que contiene la gpushape de la bala(con textura) y se escala
        bullet = sg.SceneGraphNode("bullet")
        bullet.transform = tr.scale(self.bullet_size, self.bullet_size * WIDTH/HEIGHT, 1)
        bullet.childs += [self.bullet]

        #se crea un nodo con una gpuShape que servira para detectar las colisiones(hitbox)
        collision_node = sg.SceneGraphNode("collision_bullet")
        collision_node.childs += [es.toGPUShape(cl.createCircleHitbox(BULLET_HITBOX_RADIO, 10, 0, 1, 0))]

        #posicion de donde sale la bala
        tempPos = self.position + self.bullet_pos

        #se crea uno nodo/objeto CollisionShape que tiene informacion y metodos para detectar colisiones con respecto de una gpuShape
        scaled_collision = cl.CollisionShape("scaled_collision", BULLET_HITBOX_RADIO, True)
        #se escala la hitbox para que tenga el mismo tamaño que la textura
        scaled_collision.transform = tr.scale(1, 1 * WIDTH / HEIGHT, 1)
        scaled_collision.childs += [collision_node]

        #se crea el objeto bala que contendra en como nods hijos a la textura y la hitbox
        bullet_object = go.bulletObject("playerBullet" + str(counter))
        bullet_object.fromEnemy = False #bool para saber si es una bala enemiga
        bullet_object.transform = tr.translate(tempPos[0], tempPos[1], tempPos[2]) # se ubica en la posicion inicial
        bullet_object.position = tempPos
        bullet_object.velocity[1] = BULLET_SPEED # se le asigna la velocidad vertical
        bullet_object.childs += [bullet] #se le agrega la textura
        bullet_object.childs += [scaled_collision] # se le agrega la hitbox
        bullet_object.childs[1].parent = bullet_object # se le agrega la referencia del padre al objeto CollisoinShape

        #se agrega la bala a la coleccion de balas
        bullet_collection.childs += [bullet_object]

#se obtienen ;as dimensiones de las ventanas
def setupWindowSize(width, height):
    global WIDTH, HEIGHT
    WIDTH = width
    HEIGHT = height

#inicializa la nave
def setupPlayer(image, main_node):
    #Se crean los distintos frames para cada animacion, recortando la imagen
    ship_frames1 = anim.createFrames(image, [128, 128], [0, 0], [2], [0, 0]) #animacion para avanzar
    ship_frames2 = anim.createFrames(image, [128, 128], [0, 0], [2], [0, 1]) #animacion para retroceder
    hurt_frames = anim.createFrames(image, [128, 128], [0, 0], [2], [2, 2]) # animacion cuando le llega una bala
    explode_frames = anim.createFrames(image, [128, 128], [0, 0], [2, 5], [2, 0]) # animacion de explosion

    #se crea un diccionario con las animaciones
    ship_animations = {}
    ship_animations["fast"] = anim.Animation(ship_frames1, 12, True, False)
    ship_animations["slow"] = anim.Animation(ship_frames2, 12, True, False)
    ship_animations["hurt"] = anim.Animation(hurt_frames, 12, True, False)
    ship_animations["explode"] = anim.Animation(explode_frames, 9, False, False)

    #se crea el controlador de animaciones y se inicializa
    ship_Anim = anim.Anim_Controller(ship_animations, [PLAYER_SIZE, WIDTH / HEIGHT * PLAYER_SIZE, 1], 0)
    ship_Anim.Play("slow")

    #se crea un nodo que contiene la animacion
    anim_node = sg.SceneGraphNode("anim_player")
    anim_node.childs += [ship_Anim]

    # se crea un nodo con una gpuShape que servira para detectar las colisiones y verlas si se quiere
    collision_node = sg.SceneGraphNode("collision_player")
    collision_node.childs +=  [es.toGPUShape(cl.createCircleHitbox(PLAYER_HITBOX_RADIO, 10, 0, 1, 0))]

    # se crea uno nodo/objeto CollisionShape que tiene informacion y metodos para detectar colisiones con respecto de una gpuShape
    scaled_collision = cl.CollisionShape("scaled_collision", PLAYER_HITBOX_RADIO, True)
    # se escala la hitbox para que tenga el mismo tamaño que la textura
    scaled_collision.transform = tr.scale(1, 1 * WIDTH/HEIGHT, 1)
    scaled_collision.childs += [collision_node]

    # se crea el objeto player que contendra como nodos hijos a la animacion y la hitbox
    player_gameObject = playerObject("player")
    # se traslada la nave en la pantalla a su posicion inicial
    player_gameObject.transform = tr.translate(0, -0.5, 0)
    player_gameObject.position[0] = 0
    player_gameObject.position[1] = -0.5
    player_gameObject.position[2] = 0
    player_gameObject.childs += [anim_node] #se agrega la animacion
    player_gameObject.childs += [scaled_collision] #se agrega la hitbox
    player_gameObject.childs[1].parent = player_gameObject # se agrega la referencia de padre al objeto CollisionShape

    #agrega el objeto player a la escena principal
    main_node.childs += [player_gameObject]

    #retorna la referencia al objeto player
    return go.findNode(main_node, "player")

#inicializa la coleccion de balas y su gpuShape/textura
def setupPlayerBullets(image, main_node, player):
    #recorta la imagen de la bala y crea una gpuShape
    bullet_image = anim.createFrames(image, [128, 128], [0, 0], [1], [0, 2])
    player.bullet = bullet_image[0] #se le entrega al objeto player
    #se crea al nodo que contendra las balas disparadas por Player
    bullets_collection = sg.SceneGraphNode("player_bullets")
    #se agrega la coleccion de balas al nodo principal
    main_node.childs += [bullets_collection]

    #retorna la refencia a la coleciion de balas
    return go.findNode(main_node, "player_bullets")

#Inicializa las vidas(UI) del player
def setupHearts(image, main_node):
    #recorta la imagen de los corazones y crea una gpuShape
    heart_Image =anim.createFrames(image, [128, 128], [0, 0], [1], [1, 2])
    heartGPU = heart_Image[0]
    #se crea la coleccion de corazones
    hearts_collection = sg.SceneGraphNode("hearts")
    #se añaden los corazones con los parametros definidos
    for i in range(3):
        heart = sg.SceneGraphNode("heart")
        heart.transform = tr.scale(HEART_SIZE, HEART_SIZE * WIDTH/HEIGHT, 1)
        heart.childs += [heartGPU]

        scaledHeart = go.gameObject("scaledHeart")
        scaledHeart.transform = tr.translate(HEART1_POSX + i*HEARTS_LENGTH/2, HEARTS_POSY, 0)
        scaledHeart.childs += [heart]

        hearts_collection.childs += [scaledHeart]
    #se agregan los corazones al nodo principal
    main_node.childs += [hearts_collection]
    #retorna la referencia a la coleccion de corazones
    return go.findNode(main_node, "hearts")


#se actualiza la nave y sus parametros
def updatePlayer(delta_time , player, controller, bullets, enemy_bullets, hearts, en_amount):
    global player_bullet_counter

    #Si quedan enemigos, se ejecuta la actualizacion normal de la nave(se puede mover, recibe daño, dispara, etc)
    if en_amount > 0:
        #si se ha borrado/ muerto, no hace nada
        if player == None:
            return
        #si al player no se le han acabado las vidas y esta explotando
        if not player.isExploding:

            #se actualiza las variables de posicion con los valores de traslacion
            player.position[0] = player.transform[0][3]
            player.position[1] = player.transform[1][3]
            player.position[2] = player.transform[2][3]

            #se crea la refencia al AnimController del player
            anim_player = player.childs[0].childs[0]

            #controla el tiempo en que el jugador no puede recibir daño luego de recibir un disparo
            if player.time_counter > HURTED_TIME and player.isHurted:
                player.isHurted = False
                anim_player.Play("slow")
                player.time_counter = 0
            else:
                player.time_counter += delta_time

            #se cambia la velocidad segun el input y se cambia la animacion si esta avanzando o retrocediendo
            if controller.is_up_pressed:
                player.velocity[1] +=  PLAYER_ACC
                if anim_player.current_anim == "slow" :
                    if not player.isHurted:
                        anim_player.Play("fast")
            if controller.is_down_pressed:
                player.velocity[1] -=  PLAYER_ACC
                if anim_player.current_anim == "fast" :
                    if not player.isHurted:
                        anim_player.Play("slow")

            if controller.is_right_pressed:
                player.velocity[0]+= PLAYER_ACC
            elif controller.is_left_pressed:
                player.velocity[0] -= PLAYER_ACC

            #controla el disparo y el tiempo de recarga
            if player.time_counter2 > BULLET_RELOAD_TIME and controller.is_space_press:
                player.shoot(bullets, player_bullet_counter)
                player_bullet_counter += 1
                player.time_counter2 = 0
            else:
                player.time_counter2 += delta_time

            #se normaliza la velocidad y se limita
            vel_sqr_mag=  player.velocity[0]**2 + player.velocity[1]**2
            if vel_sqr_mag > PLAYER_MAX_SPEED**2:
                player.velocity[0] = (player.velocity[0] / math.sqrt(vel_sqr_mag)) * PLAYER_MAX_SPEED
                player.velocity[1] = (player.velocity[1] / math.sqrt(vel_sqr_mag)) * PLAYER_MAX_SPEED

            #si no recibe input que mueva la nave, la velocidad se interpola para que no frene de inmediato
            if not(controller.is_up_pressed or controller.is_down_pressed or controller.is_left_pressed or controller.is_right_pressed):
                player.velocity[0] = go.lerp(player.velocity[0], 0, PLAYER_FRICC)
                player.velocity[1] = go.lerp(player.velocity[1], 0, PLAYER_FRICC)

            #la nueva posicion corresponde a la anterior mas la velocidad por un delta de tiempo
            vx = player.position[0] + player.velocity[0] * delta_time
            vy = player.position[1] + player.velocity[1] * delta_time *  WIDTH / HEIGHT #se multiplica por esta razon debido a las dimensiones de la pantalla
            vz = player.position[2] + player.velocity[2] * delta_time

            #controla que la nave no se salga de los bordes de la ventana
            if vx < -0.95:
                vx = player.position[0]
                player.velocity[0] = 0
            if vx > 0.95:
                vx = player.position[0]
                player.velocity[0] = 0
            if vy < -0.95:
                vy = player.position[1]
                player.velocity[1] = 0
            if vy > 0.92:
                vy = player.position[1]
                player.velocity[1] = 0

            #actualiza la posicion de la nave con los valores calculador
            player.transform = tr.translate(vx, vy, vz)

            #deteccion de colisiones
            if player.childs[1].canCollide:
                #funcion que entrega una referencia al nodo colisionado (o un None si no hay)
                collide_bullet = player.childs[1].collidingWith(enemy_bullets)
                if collide_bullet != None and ( not player.isHurted): #la nave detecta colisiones si no esta herida
                    collide_bullet.velocity = np.zeros(3) #la bala enemiga se detiene
                    collide_bullet.childs[1].canCollide = False #la bala enemiga ya no puede ser detectada
                    collide_bullet.childs[0].childs[0].Play("explote") #la bala enemiga explota
                    collide_bullet.isExploding = True
                    player.health -= 1 #player pierde 1 vida
                    del(hearts.childs[-1]) # se elimina un corazon

                    # si al player le queda vida, se encuentra herido por el tiempo correspondiente
                    if player.health > 0:
                        player.isHurted = True
                        player.time_counter = 0
                        anim_player.Play("hurt")
                    else:
                        #si no le queda vida, explota y no puede ser detectado
                        player.childs[1].canCollide = False
                        anim_player.Play("explode")
                        player.isExploding = True
                        player.time_counter = 0
        #si se le acabaron las vidas y esta explotando
        elif not player.isDead:
            if player.childs[0].childs[0].isFinished: #si ha terminado la animacion de explotar, esta muerto
                player.isDead = True
            if player.isDead: #si esta muerto se elimina
                player.childs[0] = sg.SceneGraphNode("None")
    else:
        #si no quedan mas enemigos, player ha ganado por lo que abandona la pantalla por arriba
        if player.childs[0].childs[0].current_anim != "fast":
            player.childs[0].childs[0].Play("fast")

        if player.position[1] < 1.5:
            player.position[0] = player.transform[0][3]
            player.position[1] = player.transform[1][3]
            player.position[2] = player.transform[2][3]

            vx = player.position[0]
            vy = player.position[1] + PLAYER_LEAVE_SPEED * delta_time * WIDTH / HEIGHT
            vz = player.position[2]
            player.transform = tr.translate(vx, vy, vz)

#se actualizan las balas de Player
def updatePlayerBullets(delta, bullets_collection):
    c = 0 #variable para contar indices
    toDelete = list() #se almacenan los indices de las balas a eliminar
    #se recorren las balas de la coleccion
    for bullet in bullets_collection.childs:
        bullet.position[0] = bullet.transform[0][3]
        bullet.position[1] = bullet.transform[1][3]
        bullet.position[2] = bullet.transform[2][3]

         #si la bala ha abandonado la pantalla, se ingresa su indice
        if bullet.position[1] > 1.2 or bullet.toDelete:
            toDelete.append(c)
            c+= 1
            continue
        #sino, se mueve segun su velocidad

        vx = bullet.position[0]
        vy = bullet.position[1] + bullet.velocity[1] * delta * WIDTH / HEIGHT
        vz = bullet.position[2]
        bullet.transform = tr.translate(vx, vy, vz)
        c += 1 #se actualiza el indice

    #se eliminan las balas
    toDelete.sort(reverse=True)
    for index in toDelete:
        del(bullets_collection.childs[index])

