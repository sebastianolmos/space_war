import glfw
from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
from PIL import Image
import sys

import transformations as tr
import basic_shapes as bs
import easy_shaders as es

# We will use 32 bits data, so we have 4 bytes
# 1 byte = 8 bits
SIZE_IN_BYTES = 4

class ImageObject:
    #Clase que sirve para contener la informacion de una imagen y asi cargarla solo una vez
    def __init__(self, fileName):
        image = Image.open(fileName)
        self.data = np.array(list(image.getdata()), np.uint8)
        self.width = image.size[0]
        self.height = image.size[1]
        if image.mode == "RGB":
            self.internalFormat = GL_RGB
            self.format = GL_RGB
        elif image.mode == "RGBA":
            self.internalFormat = GL_RGBA
            self.format = GL_RGBA
        else:
            print("Image mode not supported.")
            raise Exception()

class Animation():
    #Clase para representar una animacion
    def __init__(self, anim_frames, fps, is_looped, can_rewind):
        self.frames = anim_frames #lista con los frames de la animacion
        self.fps = fps #corresponde a la velocidad de la animacion
        self.isLooped = is_looped #Parametro booleano que indica si la animacion se debe repetir
        self.canRewind = can_rewind #Parametro que indica si esque una vez llegado al ultimo frame de la animacion, se debe realizar la animacion inversa

        self.anim_length = 0  # cantidad de frames totales a animar que depende si la animacion puede invertirse
        if self.isLooped == False:
            if self.canRewind == False:
                self.anim_length = len(self.frames)
            else:
                self.anim_length = 2 * len(self.frames) - 1

class Anim_Controller():
    #Controlador de animaciones que puede tener un objeto
    def __init__(self, animations, scale, rotation):
        self.animations = animations #diccionario que contiene las animaciones de la forma "name" : animation()
        self.isAnimated = True #booleano que indica si tiene que animarse
        self.current_anim = None #animacion actual
        self.scale = scale #escala de animacion
        self.rotation = rotation #rotacion de la animacion

        #parametros que sirven para dibujar los frames y realizar la animacion
        self.time_counter = 0 #contador de tiempo para respetar los fps de la animacion
        self.frame_counter = 0 #contador del frame que se va a dibujar
        self.isRewinding = False #parametro que indica si la animacion se esta haciendo a la inversa

        self.canPlay = True #parametro que indica si la animacion se puede ejecutar, sirve para cuando la animacion no es un loop
        self.play_counter = 0 #contador de frames para actualizar parametro canPlay
        self.isFinished = False #bool que indica si la animacion ha terminado (si esque no es un loop)

    #funcion para indicar una animacion a realizar
    def Play(self, anim_name):
        self.isFinished = False #la animacion no ha terminado
        self.current_anim = anim_name #se cambia la animacion actual
        #se iniciaizan las variables que controlan la animacion
        self.time_counter = 0
        self.frame_counter = 0
        self.isRewinding = False
        self.canPlay = True
        self.play_counter = 0

    # funcion para actualizar/dibujar la animacion
    def Update(self, pipeline, delta, transform, isPaused):
        if self.isAnimated:
            anim_to_play = self.animations[self.current_anim] #animation() actual
            owntransform = tr.matmul([transform, tr.scale(self.scale[0], self.scale[1], self.scale[2])]) #escalamiento

            if len(anim_to_play.frames) == 1:
                #si la animacion contiene un solo frame, solo se dibuja este
                glUniformMatrix4fv(glGetUniformLocation(pipeline.shaderProgram, "transform"), 1, GL_TRUE, owntransform)
                pipeline.drawShape(anim_to_play.frames[0])


            else:

                glUniformMatrix4fv(glGetUniformLocation(pipeline.shaderProgram, "transform"), 1, GL_TRUE, owntransform)
                pipeline.drawShape(anim_to_play.frames[self.frame_counter])

                if not isPaused:

                    self.time_counter += delta

                    if self.time_counter > 1 / anim_to_play.fps: #controlador de la velocidad de la animacion

                        #controlar si ya se animaron todos los frames
                        if self.play_counter >= anim_to_play.anim_length - 1:
                            self.canPlay = False
                            self.isFinished = True

                        #si quedan frames por animar o es un loop se actualizan los frames
                        if self.canPlay or anim_to_play.isLooped:
                            if anim_to_play.canRewind :
                                #si se puede invertir la animacion, los frames se actualizan segun su direccion
                                if self.isRewinding == False:
                                    self.frame_counter += 1
                                else:
                                    self.frame_counter -= 1

                                if self.frame_counter > len(anim_to_play.frames)-1:
                                    self.isRewinding = True
                                    self.frame_counter -= 2
                                elif self.frame_counter < 0 :
                                    self.isRewinding = False
                                    self.frame_counter +=2
                            else:
                                self.frame_counter = (self.frame_counter + 1 ) % len(anim_to_play.frames)
                            self.play_counter += 1

                        self.time_counter = 0

#funcion que crea una gpuShape (quad o cuadrado), a partir de una imagen cargada y una seccion de esta a recortar
def createTextureQuad(image_object, nx_i=0, ny_i=0, nx_f=1, ny_f=1, wrapMode=None, filterMode=None):
    # Defining locations and texture coordinates for each vertex of the shape
    vertexData = np.array([
        #   positions        texture
        -0.5, -0.5, 0.0, nx_i, ny_f,
        0.5, -0.5, 0.0, nx_f, ny_f,
        0.5, 0.5, 0.0, nx_f, ny_i,
        -0.5, 0.5, 0.0, nx_i, ny_i]
        , dtype=np.float32)

    # Defining connections among vertices
    # We have a triangle every 3 indices specified
    indices = np.array([
        0, 1, 2,
        2, 3, 0], dtype= np.uint32)

    # Here the new shape will be stored
    gpuShape = es.GPUShape()

    gpuShape.size = len(indices)
    gpuShape.vao = glGenVertexArrays(1)
    gpuShape.vbo = glGenBuffers(1)
    gpuShape.ebo = glGenBuffers(1)

    # Vertex data must be attached to a Vertex Buffer Object (VBO)
    glBindBuffer(GL_ARRAY_BUFFER, gpuShape.vbo)
    glBufferData(GL_ARRAY_BUFFER, len(vertexData) * SIZE_IN_BYTES, vertexData, GL_STATIC_DRAW)

    # Connections among vertices are stored in the Elements Buffer Object (EBO)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, gpuShape.ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, len(indices) * SIZE_IN_BYTES, indices, GL_STATIC_DRAW)

    gpuShape.texture = glGenTextures(1)

    glBindTexture(GL_TEXTURE_2D, gpuShape.texture)

    # texture wrapping params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrapMode)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrapMode)

    # texture filtering params
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filterMode)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filterMode)

    glTexImage2D(GL_TEXTURE_2D, 0, image_object.internalFormat, image_object.width, image_object.height, 0, image_object.format, GL_UNSIGNED_BYTE, image_object.data)

    return gpuShape

#Funcion que crea los frames de la animacion, recortando la imgen segun :
#image_object: es la imagen cargada, la cual contiene los frames a animar
#clipping es un vector2 con el tamaño de las cuadriculas que recortaran
#offset es un vector2 que contiene el desajuste que puede tener una imagen para cortar
#sprites_shape es forma(matriz) en la que estan dispuestos los frames a animar
#init_pos es un vector2 que contiene la posicion del primer frame
def createFrames(image_object, clipping, offset, sprites_shape, init_pos):
    clipping_x = clipping[0]
    clipping_y = clipping[1]
    offset_x = offset[0]
    offset_y = offset[1]
    init_pos_x = init_pos[0]
    init_pos_y = init_pos[1]

    quadSize_x = 1/image_object.width
    quadSize_y = 1 / image_object.height

    frames = list()

    if len(sprites_shape) == 1:
        for quad in range(sprites_shape[0]):
            temp_pos_x = init_pos_x + 1 *quad
            temp_pos_y = init_pos_y

            init_x =quadSize_x*clipping_x * temp_pos_x + offset_x*quadSize_x
            init_y = quadSize_y*clipping_y * temp_pos_y + offset_y*quadSize_y
            final_x = quadSize_x*clipping_x * (temp_pos_x + 1) + offset_x*quadSize_x
            final_y = quadSize_y*clipping_y * (temp_pos_y + 1) + offset_y*quadSize_y

            frames.append(createTextureQuad(image_object, init_x, init_y, final_x, final_y, GL_REPEAT, GL_NEAREST))
    elif len(sprites_shape) == 2:
        for quad_y in range(sprites_shape[0]):
            for quad_x in range(sprites_shape[1]):
                temp_pos_x = init_pos_x + 1 *quad_x
                temp_pos_y = init_pos_y + 1 *quad_y

                init_x = quadSize_x * clipping_x * temp_pos_x + offset_x * quadSize_x
                init_y = quadSize_y * clipping_y * temp_pos_y + offset_y * quadSize_y
                final_x = quadSize_x * clipping_x * (temp_pos_x + 1) + offset_x * quadSize_x
                final_y = quadSize_y * clipping_y * (temp_pos_y + 1) + offset_y * quadSize_y

                frames.append(createTextureQuad(image_object, init_x, init_y, final_x, final_y, GL_REPEAT, GL_NEAREST))

    return frames