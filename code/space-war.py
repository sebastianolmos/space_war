import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import sys

import scene_graph as sg
import animation as anim
import game_object as go
import player_object as pl
import collisions as cl
import gameover as yd
import enemies as en

FPS = 60 # FPS(frames per seconds) máximos del programa
WIDTH = 600 #Ancho de la ventana
HEIGHT = 900 #Largo de la ventana

#Se crea referencia al controller que manejara el player
controller = pl.Controller()
#Se crean objetos vacios que contendran referencias a distintas nodos de la escena
Player = None #Referencia al nodo del Player (nave que manejara el usuario)
Hearts = None #Referencia a la coleccion de nodos con las vidas del jugador (UI)
Enemies = None #Referencia a la coleccion de naves enemigas)
Enemy_Bullets = None #Referencia a la coleccion de las balas enemigas
Player_Bullets = None #Referencia a la coleccion de las balas del usuario
Universe = None #Referencia al nodo padre de toda la scena
Nebulae =None #Referencia a la coleccion de nebulosas
Stars = None #Referencia a la coleccion de estrellas
Planets = None #Referencia a la coleccion de planetas

#funcion que entrega el input del usuario
def on_key(window, key, scancode, action, mods):
    global controller

    if key == glfw.KEY_P:
        if action ==glfw.PRESS:
            controller.isPaused = not controller.isPaused
        elif action == glfw.RELEASE:
            controller.is_left_pressed = False

    if key == glfw.KEY_W:
        if action == glfw.PRESS:
            controller.is_up_pressed = True
        elif action == glfw.RELEASE:
            controller.is_up_pressed = False

    if key == glfw.KEY_S:
        if action == glfw.PRESS:
            controller.is_down_pressed = True
        elif action == glfw.RELEASE:
            controller.is_down_pressed = False

    if key == glfw.KEY_D:
        if action ==glfw.PRESS:
            controller.is_right_pressed = True
        elif action == glfw.RELEASE:
            controller.is_right_pressed = False

    if key == glfw.KEY_A:
        if action ==glfw.PRESS:
            controller.is_left_pressed = True
        elif action == glfw.RELEASE:
            controller.is_left_pressed = False

    if key == glfw.KEY_SPACE:
        if action == glfw.PRESS:
            controller.is_space_press = True
        elif action == glfw.RELEASE:
            controller.is_space_press = False

    #tecla para poder ver las collisionShape (formas de las colisiones) con que se producen las detecciones
    if key == glfw.KEY_TAB:
        if action == glfw.PRESS:
            controller.collisionShapeView = not controller.collisionShapeView

#funcion que inicializa el programa
def setup(amount):
    #se declaran las referencias como variables globales
    global Universe, Nebulae, Stars, Planets, Player, Enemies, Enemy_Bullets, Player_Bullets, Hearts

    #Se cargan las imagenes
    player_ship_image = anim.ImageObject("Sprites\playerSheet.png")
    nebulae_image = anim.ImageObject("Sprites\BG_nebulae_sheet.png")
    stars_image = anim.ImageObject("Sprites\stars_sheet.png")
    planets_image = anim.ImageObject("Sprites\planets_sheet.png")
    enemies_image = anim.ImageObject("Sprites\enemies_sheet.png")
    gameover_image = anim.ImageObject("Sprites\gameover_sheet.png")
    win_image = anim.ImageObject("Sprites\win_sheet.png")

    #Se crea el nodo principal de la escena
    Universe = sg.SceneGraphNode("Universe")

    #se entrega el tamaño de la ventana, para que otras partes del programa realizen los calculos y escalamientos de acuerdo con la ventana
    go.setupWindowSize(WIDTH, HEIGHT)
    pl.setupWindowSize(WIDTH, HEIGHT)
    en.setupWindowSize(WIDTH, HEIGHT)
    yd.setupWindowSize(WIDTH, HEIGHT)
    cl.setupWindowSize(WIDTH, HEIGHT)

    #se inicializan los objetos del programa, entregando las referencias correspondientes
    Nebulae = go.setupNebulae(nebulae_image, Universe)
    Stars = go.setupStars(stars_image, Universe)
    Planets = go.setupPlanets(planets_image, Universe)
    Enemy_Bullets = en.setupEnemyBullets(enemies_image, Universe)
    Enemies = en.setupEnemies(enemies_image, Universe, amount) #Aqui se entrega la cantidad de enemigos
    Player = pl.setupPlayer(player_ship_image, Universe)
    Player_Bullets = pl.setupPlayerBullets(player_ship_image, Universe, Player)
    Hearts = pl.setupHearts(player_ship_image, Universe)
    #inicializacion de las animaciones de ganar y perder
    yd.setupfinishAnim(gameover_image, win_image)

#funcion que actualiza cada frame las funciones que manejan los distintos objetos
def update(delta, tex_pipeline, coll_pipeline):
    enemiesAmount = en.getEnemiesAmount() + len(Enemies.childs)
    if not controller.isPaused:
        go.updateNebulae(delta, Nebulae)
        go.updateStars(delta, Stars)
        go.updatePlanets(delta, Planets)
        en.updateEnemies(delta, Enemies, Enemy_Bullets, Player_Bullets, Player)
        en.updateEnemyBullets(delta, Enemy_Bullets)
        pl.updatePlayerBullets(delta, Player_Bullets)
        pl.updatePlayer(delta, Player, controller, Player_Bullets, Enemy_Bullets, Hearts, enemiesAmount)

    #Se dibuja la escena con el pipeline de texturas
    go.drawSceneGame(Universe, tex_pipeline, "transform", delta, controller.isPaused)
    if Player.isDead:
        #Si el player muere, se ejecuta la animacion de muerte
        yd.updateGameOverAnim(delta, tex_pipeline)
    elif enemiesAmount == 0:
        #si se han eliminado todos los enemigos, se ejecuta la animacion de victoria
        yd.updateWinAnim(delta, tex_pipeline)

    if controller.collisionShapeView:
        #Si se quiere mostrar las collisionesShapes o hitbox, se utiliza su funcion de dibujo  y pipeline correpondientes.
        glUseProgram(coll_pipeline.shaderProgram)
        go.drawCollisionShapes(Universe, coll_pipeline, "transform")
        #se vuelve al pipeline de texturas
        glUseProgram(tex_pipeline.shaderProgram)

if __name__ == "__main__":

    #se recibe la cantidad de enemigos en consola
    enemy_amount = int(sys.argv[1])

    #descomentar si se quiere introducir aqui la cantidad de enemigos
    #enemy_amount = 20

    # Initialize glfw
    if not glfw.init():
        sys.exit()

    window = glfw.create_window(WIDTH, HEIGHT, "Space War", None, None)

    if not window:
        glfw.terminate()
        sys.exit()

    glfw.make_context_current(window)

    # Connecting the callback function 'on_key' to handle keyboard events
    glfw.set_key_callback(window, on_key)

    #Se definen las pipelines de texturas y collisiones
    texture_pipeline = yd.grayScaleShaderProgram() #pipeline que puede mostrar una escala de grises (utilizado en la animacion de muerte)
    collision_pipeline = cl.SimpleTransformShaderProgram() #pipeline con transparencia

    #se inicia con el pipeline de texturas
    glUseProgram(texture_pipeline.shaderProgram)

    # Setting up the clear screen color
    glClearColor(0, 0, 0, 1.0)

    # Enabling transparencies
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    #Se invoca la funcion setup que incializa el prgrama con la cantidad de enemigos
    setup(enemy_amount)

    # Get initial time
    t0 = glfw.get_time()
    time_counter = 0

    while not glfw.window_should_close(window):
        t1 = glfw.get_time()
        dt = t1 - t0
        t0 = t1

        time_counter += dt

        #Se asegura de acotar por arriba los frames con la cantidad definida
        if time_counter >= 1/FPS:
            glfw.poll_events()
            glClear(GL_COLOR_BUFFER_BIT)
            #Se invoca la funcion update que manejara el programa cada frame
            update(time_counter, texture_pipeline, collision_pipeline)

            glfw.swap_buffers(window)
            time_counter = 0


    glfw.terminate()