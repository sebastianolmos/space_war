from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import sys

import transformations as tr
import easy_shaders as es
import scene_graph as sg
import animation as anim
import game_object as go
import collisions as cl
import math
import random

ENEMIES = 3
CURRENT_ENEMY = 0 #tipo d enemigos que pertenece el grupo de enemigos actual
ENEMIES_LEFT = 0 #cantidad de enemigos que faltan aparecer
ENEMY_LEAVE_SPEED = 0.15 #velocidad en la que los enemigos dejan la pantalla al eliminar al player
ENEMY_ENABLED_POSY = 0.95 #posicion vertical de la pantalla en la que los enemigos pueden ser eliminados y pueden disparar

ENEMY0_SIZE = 0.5 #escala de enemy0 (primer tipo de enemigo)
ENEMY0_HITBOX_RADIO = 0.08 #tamaño de la hitbox del enemy0
ENEMY0_SPAWN_SPEED = 0.2 #velocidad que tiene enemy0 hasta llegar a la parte superior de la pantalla e iniciar su patron de movimientos
ENEMY0_AMOUNT = 5 #cantidad de enemy0 que tiene un grupo de estos
ENEMY0_SPAWN_POSY = 1.3 #posicion vertical donde aparece enemy0, es decir, fuera de la pantalla
ENEMY00_POSY = 0.8 #posicion en la empieza a realizar el patron de movimiento enemy0
ENEMY0_RELOAD_TIME = 0.65 #tiempo de recarga de enemy0

BULLET_SIZE = 0.5 #escala de la bala enemiga
BULLET_HITBOX_RADIO = 0.02 # tamaño de la hitbox de la bala enemiga
BULLET0_SPEED = 0.8 #velocidad de la bala disparada por enemy0
BULLET0_SAVE_ZONE_TIME = 2 #tiempo en que enemy0 deja de disparar
BULLET0_SAVED_INDEX = 0 #indice que indica que enemy0 del grupo esta dejando de disparar
BULLET0_SAVED_INCREASE = 1 #incremento que varia de positivo a negativo para hacer que la nave que deja de disparar vaya cambiando de derecha a izquierda y viceversa
BULLET0_GO_FORWARD = True #bool para realizar el patron de movimiento de enemy0

ENEMY1_SIZE = 0.5 #escala de enemy1 (segundo tipo de enemigo)
ENEMY1_HITBOX_RADIO = 0.08 #tamaño de la hitbox del enemy1
ENEMY1_SPAWN_POSY = 1.3 #posicion vertical donde aparece enemy1, es decir, fuera de la pantalla
ENEMY1_SPAWN_SPEED = 0.2 #velocidad que tiene enemy1 hasta llegar a la parte superior de la pantalla e iniciar su patron de movimiento
ENEMY1_POSY = 0.7  #posicion en la empieza a realizar el patron de movimiento enemy1
ENEMY1_AMOUNT = 6  #cantidad de enemy1 que tiene un grupo de estos
ENEMY1_SHOOT_PROBABILITY = 0.5 #Probabilidad de disparar que tiene enemy1 cada vez que termina de racarga, si no dispara vuelve a recargar
ENEMY1_RELOAD_TIME = 1 #tiempo de recarga de enemy1

BULLET1_SPEED = 0.9 #velocidad de la bala disparada por enemy1

ENEMY2_SIZE = 0.5 #escala de enemy2 (tercer tipo de enemigo)
ENEMY2_HITBOX_RADIO = 0.08 #tamaño de la hitbox del enemy2
ENEMY2_SPAWN_POSY = 1.5 #posicion vertical donde aparece enemy1, es decir, fuera de la pantalla
ENEMY2_ANGULAR_SPEED = 0.2 #velocidad con la que gira enemy2
ENEMY2_POSY = 0.7 #posicion en la que se deteiene el centro de rotacion de enemy2
ENEMY2_AMOUNT = 7 #cantidad de enemy2 que tiene un grupo de estos
ENEMY2_SHOOT_PROBABILITY = 0.3 #Probabilidad de disparar que tiene enemy1 cada vez que termina de racarga, si no dispara vuelve a recargar
ENEMY2_CENTER_SPEED = 0.2 #velocidad con la que desplaza en el centro de rotacion de un grupo de enemy2
ENEMY2_RELOAD_TIME = 0.7 #tiempo de recarga de enemy2
enemy2_center = np.zeros(2) #posicion del centro de rotacion de un grupo de enemy2
enemy2_radio = 0.35 #radio en el que giran enemy2
enemy2_canInteract = False # bool que indica si el centro de rotacion debe detenerse

BULLET2_SPEED = 0.8 #velocidad de la bala disparada por enemy2

#dimensiones de la venta no inicializados
WIDTH = 0
HEIGHT = 0

#variables globales que contienen a las animaciones/ texturas a los enemigos balas correspondientes
enemy0_animations = dict()
bullet0_animation = dict()
enemy1_animations = dict()
bullet1_animation = dict()
enemy2_animations = dict()
bullet2_animation = dict()
#contador de enemigos y balas enemigas
enemy_counter = 0
bullet_counter = 0

#contador de tiempo para el patron de movimiento de enemy0
time_counter = 0

#clase del objeto enemigo
class enemyObject(go.gameObject):
    def __init__(self, name):
        go.gameObject.__init__(self, name)
        self.health = 1 #vida
        self.enemy = 0 #tipo de enemigo (0, 1 o 2)
        self.bullet_animations = {} #animacion/textura de la bala correspondiente al tipo de enemigos
        self.bullet_pos = np.zeros(3) # posicion donde aparece la bal con respecto  a la nave enemiga
        self.canInteract = False #bool que indica ssi la nave puede empezar a realizar su patron de movimiento
        self.isExploding = False #bool que indica si esta explotando antes de desaparecer
        self.direction = np.array([1, 0]) #direccion de movimiento usado por algunos tipos de enemigos
        self.targetPos = np.zeros(2) #posicion a alcanzar para realizar el patron de movimiento de enemy1
        self.theta = 0 #angulo utilizado por enemy2

    #metodo para disparar una bala
    def shoot(self, bullet_collection, counter, speed):
        # se crea el controlador de animaciones y se inicializa con la textura
        bullet_anim = anim.Anim_Controller(self.bullet_animations, [BULLET_SIZE, BULLET_SIZE * WIDTH / HEIGHT, 1], 0)
        bullet_anim.Play("shooted") # se pone la textura de la bala
        #se crea un nodo que contiene la animacion
        scaled_bullet = sg.SceneGraphNode("scaled_bullet")
        scaled_bullet.transform = tr.rotationZ(np.pi)
        scaled_bullet.childs += [bullet_anim]

        # se crea un nodo con una gpuShape que servira para detectar las colisiones y verlas si se quiere
        collision_node = sg.SceneGraphNode("collision_enemyBullet")
        # se escala la hitbox para que tenga el mismo tamaño que la textura
        collision_node.transform = tr.scale(1, 1 * WIDTH / HEIGHT, 1)
        collision_node.childs +=  [es.toGPUShape(cl.createCircleHitbox(BULLET_HITBOX_RADIO, 10, 0, 1, 0))]

        # se crea uno nodo/objeto CollisionShape que tiene informacion y metodos para detectar colisiones con respecto de una gpuShape
        scaled_collision = cl.CollisionShape("scaled_collision", BULLET_HITBOX_RADIO, True)
        scaled_collision.transform = tr.rotationZ(np.pi) #se voltea
        scaled_collision.childs += [collision_node]

        #posicion donde aparece la bala
        tempPos = self.position + self.bullet_pos
        # se crea el objeto bullet que contendra como nodos hijos a la animacion y la hitbox
        bullet_object = go.bulletObject("bullet" + str(counter))
        bullet_object.fromEnemy = True #es bala enemiga
        # se traslada la bala en la pantalla a su posicion inicial
        bullet_object.transform = tr.translate(tempPos[0], tempPos[1], tempPos[2])
        bullet_object.position = tempPos
        bullet_object.velocity[1] = -speed #se indica su velocidad
        bullet_object.childs += [scaled_bullet] #se agrega la animacion
        bullet_object.childs += [scaled_collision] #se agrega la hitbox
        bullet_object.childs[1].parent = bullet_object # se agrega la referencia de padre al objeto CollisionShape

        #se agrega el objeto bullet a la collecion de balas enemigas
        bullet_collection.childs += [bullet_object]

#se obtienen las dimensiones de las ventanas
def setupWindowSize(width, height):
    global WIDTH, HEIGHT
    WIDTH = width
    HEIGHT = height

#entrega la cantida de enemigs restantes (sin incluir a los que hay en pantalla)
def getEnemiesAmount():
    return ENEMIES_LEFT

#inicializa los enemigos
def setupEnemies(image, main_node, enemies_amount):
    global enemy0_animations, enemy1_animations, enemy2_animations, ENEMIES_LEFT, CURRENT_ENEMY

    # ENEMY0 SETUP
    enemy0_flying_frames = anim.createFrames(image, [64, 64], [0, 0], [4], [0, 0]) #se recorta la imagen
    enemy0_explote_frames = anim.createFrames(image, [64, 64], [0, 0], [9], [0, 1])
    #se crean las animaciones
    enemy0_flying_anim = anim.Animation(enemy0_flying_frames, 12, True, False)
    enemy0_explote_anim = anim.Animation(enemy0_explote_frames, 12, False, False)
    #se crea la agrupacion de animaciones
    enemy0_animations = {"flying" : enemy0_flying_anim, "explote" : enemy0_explote_anim}

    #ENEMY1 SETUP
    enemy1_flying_frames = anim.createFrames(image, [64, 64], [0, 0], [4], [0, 4]) #se recorta la imagen
    enemy1_explote_frames = anim.createFrames(image, [64, 64], [0, 0], [9], [0, 5])
    # se crean las animaciones
    enemy1_flying_anim = anim.Animation(enemy1_flying_frames, 12, True, False)
    enemy1_explote_anim = anim.Animation(enemy1_explote_frames, 12, False, False)
    # se crea la agrupacion de animaciones
    enemy1_animations = {"flying": enemy1_flying_anim, "explote": enemy1_explote_anim}

    # ENEMY2 SETUP
    enemy2_flying_frames = anim.createFrames(image, [64, 64], [0, 0], [4], [0, 8]) #se recorta la imagen
    enemy2_explote_frames = anim.createFrames(image, [64, 64], [0, 0], [9], [0, 9])
    # se crean las animaciones
    enemy2_flying_anim = anim.Animation(enemy2_flying_frames, 12, True, False)
    enemy2_explote_anim = anim.Animation(enemy2_explote_frames, 12, False, False)
    # se crea la agrupacion de animaciones
    enemy2_animations = {"flying": enemy2_flying_anim, "explote": enemy2_explote_anim}

    #se crea la coleccion de enmigos y se agrega al nodo principal
    enemies_collection = sg.SceneGraphNode("enemies")
    main_node.childs += [enemies_collection]
    Enemies = go.findNode(main_node, "enemies")

    #se define la cantidad de enemigos restantes
    ENEMIES_LEFT = enemies_amount
    #se elige un tipo de enemigos aleatoriamente
    random_enemy = random.randint(0, ENEMIES - 1)
    if enemies_amount <=5:
        #si la cantidad de enemigos es menor a 5 apaarece un grupo de enemy1
        addEnemies1(Enemies, enemies_amount)
        ENEMIES_LEFT -= enemies_amount
        CURRENT_ENEMY = 1
    elif random_enemy == 0:
        #aparece un grupo de enemy0 y se actualizan las variables
        addEnemies0(Enemies, ENEMY0_AMOUNT)
        ENEMIES_LEFT -= ENEMY0_AMOUNT
        CURRENT_ENEMY = 0
    elif random_enemy == 1:
        # aparece un grupo de enemy1 y se actualizan las variables
        addEnemies1(Enemies, ENEMY1_AMOUNT)
        ENEMIES_LEFT -= ENEMY1_AMOUNT
        CURRENT_ENEMY = 1
    elif random_enemy == 2:
        # aparece un grupo de enemy2 y se actualizan las variables
        addEnemies2(Enemies, ENEMY2_AMOUNT)
        ENEMIES_LEFT -= ENEMY2_AMOUNT
        CURRENT_ENEMY = 2

    #retorna una referencia a la coleccion de enemigos
    return Enemies

#inicializa las balas enemigas

def setupEnemyBullets(image, main_node):
    global bullet0_animation, bullet1_animation, bullet2_animation
    #ENEMY 0 BULLET SETUP
    bullet0_image = anim.createFrames(image, [64, 64], [0, 0], [1], [0, 2]) #se recorta la imagen
    bullet0_explote_frames = anim.createFrames(image, [64, 64], [0, 0], [6], [0, 3])
    # se crean las animaciones
    bullet0_anim = anim.Animation(bullet0_image, 1, True, False)
    bullet0_explote_anim = anim.Animation(bullet0_explote_frames, 12, False, False)
    # se crea la agrupacion de animaciones
    bullet0_animation = {"shooted" : bullet0_anim, "explote" : bullet0_explote_anim}

    # ENEMY 1 BULLET SETUP
    bullet1_image = anim.createFrames(image, [64, 64], [0, 0], [1], [0, 6]) #se recorta la imagen
    bullet1_explote_frames = anim.createFrames(image, [64, 64], [0, 0], [6], [0, 7])
    # se crean las animaciones
    bullet1_anim = anim.Animation(bullet1_image, 1, True, False)
    bullet1_explote_anim = anim.Animation(bullet1_explote_frames, 12, False, False)
    # se crea la agrupacion de animaciones
    bullet1_animation = {"shooted": bullet1_anim, "explote": bullet1_explote_anim}

    # ENEMY 2 BULLET SETUP
    bullet2_image = anim.createFrames(image, [64, 64], [0, 0], [1], [0, 10]) #se recorta la imagen
    bullet2_explote_frames = anim.createFrames(image, [64, 64], [0, 0], [6], [0, 11])
    # se crean las animaciones
    bullet2_anim = anim.Animation(bullet2_image, 1, True, False)
    bullet2_explote_anim = anim.Animation(bullet2_explote_frames, 12, False, False)
    # se crea la agrupacion de animaciones
    bullet2_animation = {"shooted": bullet2_anim, "explote": bullet2_explote_anim}

    # se crea la coleccion de balas y se agrega al nodo principal
    bullets_collection = sg.SceneGraphNode("enemy_bullets")
    main_node.childs += [bullets_collection]

    # retorna una referencia a la coleccion de balas enemigas
    return go.findNode(main_node, "enemy_bullets")

#añade un grupo de enemy0
def addEnemies0(enemies_collection, amount):
    global enemy_counter
    #se distribuyen los enemigos en la pantalla segun su cantidad
    for enemy in range(amount):
        # se crea el controlador de animaciones y se inicializa
        enemy_anim = anim.Anim_Controller(enemy0_animations, [ENEMY0_SIZE, ENEMY0_SIZE * WIDTH/HEIGHT, 1], 0)
        enemy_anim.Play("flying")
        #se define su posicion horizontal
        temp_posX = -1 + 1/amount -0.05 + enemy*(2/amount)

        # se crea un nodo que contiene la animacion y que la voltea
        scaled_enemy = sg.SceneGraphNode("scaled_enemy")
        scaled_enemy.transform = tr.rotationZ(np.pi)
        scaled_enemy.childs += [enemy_anim]

        # se crea un nodo con una gpuShape que servira para detectar las colisiones y verlas si se quiere
        collision_node = sg.SceneGraphNode("collision_enemy0")
        collision_node.transform = tr.scale(1, 1* WIDTH / HEIGHT, 1)
        collision_node.childs +=  [es.toGPUShape(cl.createCircleHitbox(ENEMY0_HITBOX_RADIO, 10, 0, 1, 0))]

        # se crea uno nodo/objeto CollisionShape que tiene informacion y metodos para detectar colisiones con respecto de una gpuShape
        scaled_collision = cl.CollisionShape("scaled_collision", ENEMY0_HITBOX_RADIO, True)
        scaled_collision.transform = tr.rotationZ(np.pi)
        scaled_collision.childs += [collision_node]

        # se crea el objeto enemy que contendra como nodos hijos a la animacion y la hitbox
        enemy_object = enemyObject("enemy" + str(enemy_counter))
        enemy_object.enemy = 0 # es el primer tipo de enmigos
        # se traslada la nave en la pantalla a su posicion inicial
        enemy_object.transform = tr.translate(temp_posX, ENEMY0_SPAWN_POSY, 0)
        enemy_object.position[0] = temp_posX
        enemy_object.position[1] = ENEMY0_SPAWN_POSY
        enemy_object.position[2] = 0
        #se indica su velocidad
        enemy_object.velocity = [0, ENEMY0_SPAWN_SPEED, 0]
        enemy_object.childs += [scaled_enemy] #se agrega la animacion
        enemy_object.childs += [scaled_collision] #se agrega la hitbox
        enemy_object.childs[1].parent = enemy_object # se agrega la referencia de padre al objeto CollisionShape

        #se le agrega la animacion de su bala correspondiente
        enemy_object.bullet_animations = bullet0_animation
        enemy_counter += 1
        #se agrega el objeto enemy a la collecion de enemigos
        enemies_collection.childs += [enemy_object]

#añade un grupo de enemy1
def addEnemies1(enemies_collection, amount):
    global enemy_counter
    # se distribuyen los enemigos en la pantalla segun su cantidad
    for enemy in range(amount):
        # se crea el controlador de animaciones y se inicializa
        enemy_anim = anim.Anim_Controller(enemy1_animations, [ENEMY1_SIZE, ENEMY1_SIZE * WIDTH/HEIGHT, 1], 0)
        enemy_anim.Play("flying")
        # se define su posicion horizontal
        temp_posX = -1 +0.07 + enemy*(2/amount)

        # se crea un nodo que contiene la animacion y que la voltea
        scaled_enemy = sg.SceneGraphNode("scaled_enemy")
        scaled_enemy.transform = tr.rotationZ(np.pi)
        scaled_enemy.childs += [enemy_anim]

        # se crea un nodo con una gpuShape que servira para detectar las colisiones y verlas si se quiere
        collision_node = sg.SceneGraphNode("collision_enemy1")
        collision_node.transform = tr.scale(1, 1* WIDTH / HEIGHT, 1)
        collision_node.childs += [es.toGPUShape(cl.createCircleHitbox(ENEMY1_HITBOX_RADIO, 10, 0, 1, 0))]

        # se crea uno nodo/objeto CollisionShape que tiene informacion y metodos para detectar colisiones con respecto de una gpuShape
        scaled_collision = cl.CollisionShape("scaled_collision", ENEMY1_HITBOX_RADIO, True)
        scaled_collision.transform = tr.rotationZ(np.pi)
        scaled_collision.childs += [collision_node]

        # se crea el objeto enemy que contendra como nodos hijos a la animacion y la hitbox
        enemy_object = enemyObject("enemy" + str(enemy_counter))
        enemy_object.enemy = 1  # es el segundo tipo de enemigos
        # se traslada la nave en la pantalla a su posicion inicial
        enemy_object.transform = tr.translate(temp_posX, ENEMY1_SPAWN_POSY, 0)
        enemy_object.position[0] = temp_posX
        enemy_object.position[1] = ENEMY1_SPAWN_POSY
        enemy_object.position[2] = 0
        enemy_object.velocity = [0, ENEMY1_SPAWN_SPEED, 0] #se indica su velocidad
        enemy_object.childs += [scaled_enemy] #se agrega la animacion
        enemy_object.childs += [scaled_collision] #se agrega la hitbox
        enemy_object.childs[1].parent = enemy_object  # se agrega la referencia de padre al objeto CollisionShape

        # se le agrega la animacion de su bala correspondiente
        enemy_object.bullet_animations = bullet1_animation
        enemy_counter += 1

        # se agrega el objeto enemy a la coleccion de enemigos
        enemies_collection.childs += [enemy_object]

#añade un grupo de enemy2
def addEnemies2(enemies_collection, amount):
    global enemy_counter, enemy2_center
    #se inicializan los valores para el centro de rotacion
    enemy2_center[0] = 0
    enemy2_center[1] = ENEMY2_SPAWN_POSY
    #angulo para distribuir radialmente a las naves
    tempTheta = 2 * np.pi / amount
    # se distribuyen los enemigos en la pantalla segun su cantidad
    for enemy in range(amount):
        # se crea el controlador de animaciones y se inicializa
        enemy_anim = anim.Anim_Controller(enemy2_animations, [ENEMY2_SIZE, ENEMY2_SIZE * WIDTH/HEIGHT, 1], 0)
        enemy_anim.Play("flying")
        # se define su posicion
        temp_posX = enemy2_center[0] + enemy2_radio * math.cos(tempTheta * enemy) * 2.5
        temp_posY = enemy2_center[1] + enemy2_radio * math.sin(tempTheta * enemy)* WIDTH / HEIGHT

        # se crea un nodo que contiene la animacion y que la voltea
        scaled_enemy = sg.SceneGraphNode("scaled_enemy")
        scaled_enemy.transform = tr.rotationZ(np.pi)
        scaled_enemy.childs += [enemy_anim]

        # se crea un nodo con una gpuShape que servira para detectar las colisiones y verlas si se quiere
        collision_node = sg.SceneGraphNode("collision_enemy2")
        collision_node.transform = tr.scale(1, 1* WIDTH / HEIGHT, 1)
        collision_node.childs +=  [es.toGPUShape(cl.createCircleHitbox(ENEMY2_HITBOX_RADIO, 10, 0, 1, 0))]

        # se crea uno nodo/objeto CollisionShape que tiene informacion y metodos para detectar colisiones con respecto de una gpuShape
        scaled_collision = cl.CollisionShape("scaled_collision", ENEMY2_HITBOX_RADIO, True)
        scaled_collision.transform = tr.rotationZ(np.pi)
        scaled_collision.childs += [collision_node]

        # se crea el objeto enemy que contendra como nodos hijos a la animacion y la hitbox
        enemy_object = enemyObject("enemy" + str(enemy_counter))
        enemy_object.theta = tempTheta * enemy
        enemy_object.enemy = 2 # es el tercer tipo de enemigos
        # se traslada la nave en la pantalla a su posicion inicial
        enemy_object.transform = tr.translate(temp_posX, temp_posY, 0)
        enemy_object.position[0] = temp_posX
        enemy_object.position[1] = temp_posY
        enemy_object.position[2] = 0
        enemy_object.velocity = [0, ENEMY2_CENTER_SPEED, 0] #se indica la velocidad del centro de rotacion
        enemy_object.childs += [scaled_enemy] #se agrega la animacion
        enemy_object.childs += [scaled_collision] #se agrega la hitbox
        enemy_object.childs[1].parent = enemy_object # se agrega la referencia de padre al objeto CollisionShape

        # se le agrega la animacion de su bala correspondiente
        enemy_object.bullet_animations = bullet2_animation
        enemy_counter += 1

        # se agrega el objeto enemy a la coleccion de enemigos
        enemies_collection.childs += [enemy_object]

#actualiza a las naves enemigas
def updateEnemies(delta, enemies_collection, bullet_collection, player_bullets, player):
    global ENEMIES_LEFT, CURRENT_ENEMY, enemy2_center, enemy2_canInteract

    #si el player no ha muerto, realizan su comportamiento normalmente
    if not player.isExploding:
        #si la coleccion no tiene enemigos y quedan enemigos por invocar, aparece otro grupo de enmigos aleatorioamente
        if len(enemies_collection.childs) == 0 and ENEMIES_LEFT > 0:
            #grupo de enemigos a invocar
            random_enemy = random.randint(0, ENEMIES - 1)
            #si quedan menos de 5 enemigos por mostrar, aparece un grupo de enemy1
            if ENEMIES_LEFT <= 5:
                addEnemies1(enemies_collection, ENEMIES_LEFT)
                ENEMIES_LEFT -= ENEMIES_LEFT
                CURRENT_ENEMY = 1
            elif random_enemy == 0:
                # aparece un grupo de enemy0 y se actualizan las variables
                addEnemies0(enemies_collection, ENEMY0_AMOUNT)
                ENEMIES_LEFT -= ENEMY0_AMOUNT
                CURRENT_ENEMY = 0
            elif random_enemy == 1:
                # aparece un grupo de enemy1 y se actualizan las variables
                addEnemies1(enemies_collection, ENEMY1_AMOUNT)
                ENEMIES_LEFT -= ENEMY1_AMOUNT
                CURRENT_ENEMY = 1
            elif random_enemy == 2:
                # aparece un grupo de enemy2 y se actualizan las variables
                enemy2_center = np.zeros(2)
                enemy2_canInteract = False
                addEnemies2(enemies_collection, ENEMY2_AMOUNT)
                ENEMIES_LEFT -= ENEMY2_AMOUNT
                CURRENT_ENEMY = 2

        #se actualizan los enenmigos actuales dependiendo del typo de enemigos que son
        if CURRENT_ENEMY == 0:
            updateEnemies0(delta, enemies_collection, bullet_collection, player_bullets)
        elif CURRENT_ENEMY == 1:
            updateEnemies1(delta, enemies_collection, bullet_collection, player_bullets)
        elif CURRENT_ENEMY == 2:
            updateEnemies2(delta, enemies_collection, bullet_collection, player_bullets)
    else:
        #si player ha sdo eliminado, abandonan la pantalla por abajo
        for enemy in enemies_collection.childs:
            if enemy.position[1] > -1.5:
                enemy.position[0] = enemy.transform[0][3]
                enemy.position[1] = enemy.transform[1][3]
                enemy.position[2] = enemy.transform[2][3]

                vx = enemy.position[0]
                vy = enemy.position[1] - ENEMY_LEAVE_SPEED * delta * WIDTH / HEIGHT
                vz = enemy.position[2]
                enemy.transform = tr.translate(vx, vy, vz)

#Actualiza el primer tipo de enemigos
def updateEnemies0(delta, enemies_collection, bullet_collection, player_bullets):
    global time_counter, BULLET0_SAVED_INDEX, BULLET0_SAVED_INCREASE, bullet_counter, BULLET0_GO_FORWARD

    #Cada cierto tiempo se va actualizando el indice que indica cual enemigo no esta disparando
    if time_counter > BULLET0_SAVE_ZONE_TIME:
        time_counter = 0
        if len(enemies_collection.childs) == 1:
            BULLET0_SAVED_INDEX = (BULLET0_SAVED_INDEX + 1)% 2
        else:
            BULLET0_SAVED_INDEX = BULLET0_SAVED_INDEX + BULLET0_SAVED_INCREASE
            if BULLET0_SAVED_INDEX > len(enemies_collection.childs) - 1:
                BULLET0_SAVED_INCREASE = -1
                BULLET0_SAVED_INDEX = len(enemies_collection.childs) - 2
            elif BULLET0_SAVED_INDEX < 0:
                BULLET0_SAVED_INCREASE = 1
                BULLET0_SAVED_INDEX = 1

        #tambien  se actualiza el bool que indica si los eneigos se estan moviendo diagonalmente hacia arriba o aabajo
        BULLET0_GO_FORWARD = not BULLET0_GO_FORWARD

    s = 0 #indice al recorrer la coleccion de enemigos para ver que enemigo puede disparar
    c = 0  #indice al recorrer la coleccion de enemigos para ver que enemigos hay que eliminar
    toDelete = list() # lista para contener los indices de los enemigos a borrar

    #se recorren la lista de enemigos
    for enemy in enemies_collection.childs:
        #si el enemigo ha terminado de explotar se elimina
        if enemy.isExploding:
            if enemy.childs[0].childs[0].isFinished:
                toDelete.append(c)
        # si no esta explotando y tiene vida
        elif enemy.health>0:
            if (not enemy.canInteract) :
                #si no puede interactuar se encuentra dirigiendose a la parte superior de la pantalla, donde hara su patron de movimiento
                if enemy.position[1] > ENEMY00_POSY:
                    #se desplaza hacia abajo
                    enemy.position[0] = enemy.transform[0][3]
                    enemy.position[1] = enemy.transform[1][3]
                    enemy.position[2] = enemy.transform[2][3]

                    vx = enemy.position[0]
                    vy = enemy.position[1] - enemy.velocity[1] * delta * WIDTH / HEIGHT
                    vz = enemy.position[2]
                    enemy.transform = tr.translate(vx, vy, vz)

                    #si aparece en la pantalla puede recibir disparos y disparar
                    if enemy.position[1] < ENEMY_ENABLED_POSY:
                        #dispara cada ve que termina de recargar y la probabilidad de disparo lo deje
                        if enemy.time_counter > ENEMY0_RELOAD_TIME:
                            ran_prob = random.random()
                            if ran_prob <= ENEMY1_SHOOT_PROBABILITY:
                                enemy.shoot(bullet_collection, bullet_counter, BULLET0_SPEED)
                                bullet_counter += 1
                            enemy.time_counter = 0
                        enemy.time_counter += delta
                        #se detectan colisiones
                        collide_bullet = enemy.childs[1].collidingWith(player_bullets)
                        if collide_bullet != None:
                            #se ha encontrado una bala del player
                            enemy.childs[1].parent.health -= 1
                            enemy.childs[1].canCollide = False
                            enemy.childs[0].childs[0].Play("explote")
                            enemy.isExploding = True #empieza a explotar
                            collide_bullet.toDelete = True

                else:
                    #empieza ha realizar su patron de movimiento
                    enemy.canInteract = True
            else :
                #patron de movimiento
                if BULLET0_GO_FORWARD:
                    #se mueve diagonalmente hacia arriba
                    enemy.position[0] = enemy.transform[0][3]
                    enemy.position[1] = enemy.transform[1][3]
                    enemy.position[2] = enemy.transform[2][3]

                    vx = enemy.position[0] + enemy.velocity[1] * delta * 0.3
                    vy = enemy.position[1] + enemy.velocity[1] * delta * WIDTH / HEIGHT* 0.3
                    vz = enemy.position[2]
                    enemy.transform = tr.translate(vx, vy, vz)
                else:
                    # se mueve diagonalmente hacia abajo
                    enemy.position[0] = enemy.transform[0][3]
                    enemy.position[1] = enemy.transform[1][3]
                    enemy.position[2] = enemy.transform[2][3]

                    vx = enemy.position[0] - enemy.velocity[1] * delta* 0.3
                    vy = enemy.position[1] - enemy.velocity[1] * delta * WIDTH / HEIGHT* 0.3
                    vz = enemy.position[2]
                    enemy.transform = tr.translate(vx, vy, vz)

                #disparo
                if enemy.time_counter > ENEMY0_RELOAD_TIME:
                    if s != BULLET0_SAVED_INDEX:
                        #dispara si ya ha recargado y el indice le indica que puede
                            enemy.shoot(bullet_collection, bullet_counter, BULLET0_SPEED)
                            bullet_counter += 1
                    enemy.time_counter = 0
                enemy.time_counter += delta
                s += 1

                # se detectan colisiones
                collide_bullet = enemy.childs[1].collidingWith(player_bullets)
                if collide_bullet != None:
                    # se ha encontrado una bala del player
                    enemy.childs[1].parent.health -= 1
                    enemy.childs[1].canCollide = False # ya no puede ser detectado
                    enemy.childs[0].childs[0].Play("explote") #empieza a explotar
                    enemy.isExploding = True
                    collide_bullet.toDelete = True
        c += 1

    #se actualiza el contador
    time_counter += delta
    # se eliminan los enemigos que corresponden
    toDelete.sort(reverse=True)
    for index in toDelete:
        del(enemies_collection.childs[index])

#Actualiza el segundo tipo de enemigos
def updateEnemies1(delta, enemies_collection, bullet_collection, player_bullets):
    global bullet_counter

    c = 0 #indice al recorrer la coleccion de enemigos para ver que enemigos hay que eliminar
    toDelete = list()  # lista para contener los indices de los enemigos a borrar

    # se recorren la lista de enemigos
    for enemy in enemies_collection.childs:
        # si el enemigo ha terminado de explotar se elimina
        if enemy.isExploding:
            if enemy.childs[0].childs[0].isFinished:
                toDelete.append(c)

        elif enemy.health > 0:
            # si no esta explotando y tiene vida
            if (not enemy.canInteract):
            # si no puede interactuar se encuentra dirigiendose a la parte superior de la pantalla, donde hara su patron de movimiento
                if enemy.position[1] > ENEMY1_POSY:
                # se desplaza hacia abajo
                    enemy.position[0] = enemy.transform[0][3]
                    enemy.position[1] = enemy.transform[1][3]
                    enemy.position[2] = enemy.transform[2][3]

                    vx = enemy.position[0]
                    vy = enemy.position[1] - enemy.velocity[1] * delta * WIDTH / HEIGHT
                    vz = enemy.position[2]
                    enemy.transform = tr.translate(vx, vy, vz)

                    # si aparece en la pantalla puede recibir disparos y disparar
                    if enemy.position[1] < ENEMY_ENABLED_POSY:
                        # dispara cada ve que termina de recargar y la probabilidad de disparo lo deje
                        if enemy.time_counter > ENEMY1_RELOAD_TIME:
                            ran_prob = random.random()
                            if ran_prob <= ENEMY1_SHOOT_PROBABILITY:
                                enemy.shoot(bullet_collection, bullet_counter, BULLET1_SPEED)
                                bullet_counter += 1
                            enemy.time_counter = 0
                        enemy.time_counter += delta
                        # se detectan colisiones
                        collide_bullet = enemy.childs[1].collidingWith(player_bullets)
                        if collide_bullet != None:
                            # se ha encontrado una bala del player
                            enemy.childs[1].parent.health -= 1
                            enemy.childs[1].canCollide = False  # ya no puede ser detectado
                            enemy.childs[0].childs[0].Play("explote")  #empieza a explotar
                            enemy.isExploding = True
                            collide_bullet.toDelete = True

                else:
                    # empieza ha realizar su patron de movimiento
                    enemy.canInteract = True
                    tempPos = np.array([enemy.position[0], enemy.position[1]])
                    #se indica la ppsicion a alcanzar
                    enemy.targetPos = tempPos + np.array([enemy.direction[0] * (2 / ENEMY1_AMOUNT), 0.6 * enemy.direction[1] * (2 / ENEMY1_AMOUNT)])
            else:
                # patron de movimiento
                tempPos = np.array([enemy.position[0], enemy.position[1]])
                distance = (tempPos[0] - enemy.targetPos[0])**2 + (tempPos[1] - enemy.targetPos[1])**2
                if distance > 0.001:
                    #no ha alcanzado la targetPos, entonces se mueve hacia esa posicion
                    enemy.position[0] = enemy.transform[0][3]
                    enemy.position[1] = enemy.transform[1][3]
                    enemy.position[2] = enemy.transform[2][3]

                    vx = enemy.position[0] + enemy.velocity[1] * delta * enemy.direction[0] * 0.5
                    vy = enemy.position[1] + enemy.velocity[1] * delta * WIDTH / HEIGHT * enemy.direction[1] * 0.5
                    vz = enemy.position[2]
                    enemy.transform = tr.translate(vx, vy, vz)
                else:
                    #si ya a alcanzado la targetPos se actualiza esta y la direccion a seguir para formar el movimientro rectangular
                    if enemy.direction[0] == 1 and enemy.direction[1] == 0:
                        enemy.direction[0] = 0
                        enemy.direction[1] = -1
                    elif enemy.direction[0] == 0 and enemy.direction[1] == -1:
                        enemy.direction[0] = -1
                        enemy.direction[1] = 0
                    elif enemy.direction[0] == -1 and enemy.direction[1] == 0:
                        enemy.direction[0] = 0
                        enemy.direction[1] = 1
                    elif enemy.direction[0] == 0 and enemy.direction[1] == 1:
                        enemy.direction[0] = 1
                        enemy.direction[1] = 0
                    tempPos = np.array([enemy.position[0], enemy.position[1]])
                    enemy.targetPos = tempPos + np.array([enemy.direction[0] * (2 / ENEMY1_AMOUNT),  0.6 * enemy.direction[1] * (2 / ENEMY1_AMOUNT)])

                # dispara cada ve que termina de recargar y la probabilidad de disparo lo deje
                if enemy.time_counter > ENEMY1_RELOAD_TIME:
                    ran_prob = random.random()
                    if ran_prob <= ENEMY1_SHOOT_PROBABILITY:
                        enemy.shoot(bullet_collection, bullet_counter, BULLET1_SPEED)
                        bullet_counter += 1
                    enemy.time_counter = 0
                enemy.time_counter += delta

                # se detectan colisiones
                collide_bullet = enemy.childs[1].collidingWith(player_bullets)
                if collide_bullet != None:
                    # se ha encontrado una bala del player
                    enemy.childs[1].parent.health -= 1
                    enemy.childs[1].canCollide = False  # ya no puede ser detectado
                    enemy.childs[0].childs[0].Play("explote") #empieza a explotar
                    enemy.isExploding = True
                    collide_bullet.toDelete = True
        c += 1

    # se eliminan los enemigos que corresponden
    toDelete.sort(reverse=True)
    for index in toDelete:
        del(enemies_collection.childs[index])

#Actualiza el tercer tipo de enemigos
def updateEnemies2(delta, enemies_collection, bullet_collection, player_bullets):
    global bullet_counter, enemy2_center, enemy2_canInteract

    #actualiza la velocidad angular segun la cantidad de enemigos del grupo, es decir, entre menos enemigos del grupo, los que quedan se movean a mayor velocidad
    tempSpeed = ENEMY2_ANGULAR_SPEED * ENEMY2_AMOUNT
    tempangSpeed = tempSpeed / len(enemies_collection.childs)

    if not enemy2_canInteract:
        #los enemigos pueden interactuar solamente cuando su centro de rotacion haya alcanzado la parte suprior de la pantalla
        if enemy2_center[1] > ENEMY2_POSY:
            enemy2_center[1] -= ENEMY2_CENTER_SPEED * delta * WIDTH / HEIGHT
        else:
            enemy2_canInteract = True

    c = 0 #indice al recorrer la coleccion de enemigos para ver que enemigos hay que eliminar
    toDelete = list()  # lista para contener los indices de los enemigos a borrar

    # se recorren la lista de enemigos
    for enemy in enemies_collection.childs:
        # si el enemigo ha terminado de explotar se elimina
        if enemy.isExploding:
            if enemy.childs[0].childs[0].isFinished:
                toDelete.append(c)

        elif enemy.health > 0:
            #si esta vivo se movera en torno a su centro de rotacion en forma de un circulo achatado verticalmente
            vx = enemy2_center[0] + enemy2_radio * math.cos(enemy.theta) * 2.5
            vy = enemy2_center[1] - enemy2_radio * math.sin(enemy.theta) * WIDTH / HEIGHT
            vz = enemy.position[2]

            enemy.transform = tr.translate(vx, vy, vz)

            #se actualiza su angulo con la velocidad angular calculada
            enemy.theta += tempangSpeed * delta
            #se actualiza las variables que guardan la posicion
            enemy.position[0] = enemy.transform[0][3]
            enemy.position[1] = enemy.transform[1][3]
            enemy.position[2] = enemy.transform[2][3]

            # si puede interectar o aparece en la pantalla puede recibir disparos y disparar
            if enemy2_canInteract  or enemy.position[1] < ENEMY_ENABLED_POSY:
                # dispara cada ve que termina de recargar y la probabilidad de disparo lo deje
                if enemy.time_counter > ENEMY2_RELOAD_TIME:
                    ran_prob = random.random()
                    if ran_prob <= ENEMY2_SHOOT_PROBABILITY:
                        enemy.shoot(bullet_collection, bullet_counter, BULLET2_SPEED)
                        bullet_counter += 1
                    enemy.time_counter = 0
                enemy.time_counter += delta

                # se detectan colisiones
                collide_bullet = enemy.childs[1].collidingWith(player_bullets)
                if collide_bullet != None:
                    # se ha encontrado una bala del player
                    enemy.childs[1].parent.health -= 1
                    enemy.childs[1].canCollide = False # ya no puede ser detectado
                    enemy.childs[0].childs[0].Play("explote") #empieza a explotar
                    enemy.isExploding = True
                    collide_bullet.toDelete = True
        c += 1
    toDelete.sort(reverse=True)
    for index in toDelete:
        del(enemies_collection.childs[index])

#se actualizan las balas disparadas por naves enemigas
def updateEnemyBullets(delta, bullets_collection):
    c = 0 #variable para contar indices
    toDelete= list()  #se almacenan los indices de las balas a eliminar
    # se recorren las balas de la coleccion
    for bullet in bullets_collection.childs:
        # si la bala ha terminado de explotar se elimina
        if bullet.isExploding:
            if bullet.childs[0].childs[0].isFinished:
                toDelete.append(c)
        else: #no esta explotando
            bullet.position[0] = bullet.transform[0][3]
            bullet.position[1] = bullet.transform[1][3]
            bullet.position[2] = bullet.transform[2][3]

            # si la bala ha abandonado la pantalla, se elimina
            if bullet.position[1] < -1.1  :
                toDelete.append(c)

            else:# sino, se mueve segun su velocidad
                vx = bullet.position[0]
                vy = bullet.position[1] + bullet.velocity[1] * delta * WIDTH / HEIGHT
                vz = bullet.position[2]
                bullet.transform = tr.translate(vx, vy, vz)
        c += 1
    # se eliminan las balas
    toDelete.sort(reverse=True)
    for index in toDelete:
        del(bullets_collection.childs[index])

