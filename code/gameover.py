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

#dimensiones de la venta no inicializados
WIDTH = 0
HEIGHT = 0
#fondo de la animacion game over
BACKGROUND_ANIM = None
#letras de la animacion de gameOver
LETTERS_ANIM = None
#animacion de victoria
WIN_ANIM = None

scale = 0 #escala que varia
color = 1 # color que varia par la escala de grises

#Pipeline que permite  poner las texturas en escala de grises
class grayScaleShaderProgram:
    def __init__(self):
        vertex_shader = """
            #version 130

            uniform mat4 transform;

            in vec3 position;
            in vec2 texCoords;

            out vec2 outTexCoords;

            void main()
            {
                gl_Position = transform * vec4(position, 1.0f);
                outTexCoords = texCoords;
            }
            """

        fragment_shader = """
                    #version 130

                    in vec2 outTexCoords;

                    out vec4 outColor;

                    uniform sampler2D samplerTex;

                    void main()
                    {   
                        outColor = texture(samplerTex, outTexCoords);
                    }
                    """

        self.shaderProgram = OpenGL.GL.shaders.compileProgram(
            OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER),
            OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER))

    #funcion que interpola los colores a una escala de grises, con index = 1 se tienen los colores normales y con index = 0 se obtienen una escala de grises total
    def grayScale(self, index):
        vertex_shader = """
                    #version 130

                    uniform mat4 transform;

                    in vec3 position;
                    in vec2 texCoords;

                    out vec2 outTexCoords;

                    void main()
                    {
                        gl_Position = transform * vec4(position, 1.0f);
                        outTexCoords = texCoords;
                    }
                    """

        fragment_shader = f"""
            #version 130

            in vec2 outTexCoords;

            out vec4 outColor;

            uniform sampler2D samplerTex;

            void main()
            {{   
                float temp0 = texture(samplerTex, outTexCoords)[0];
                float temp1 = texture(samplerTex, outTexCoords)[1];
                float temp2 = texture(samplerTex, outTexCoords)[2];
                float temp3 = texture(samplerTex, outTexCoords)[3];
                float meanColor = (temp0 + temp1 + temp2) /3;
                float weight = {index};
                float interpol0 = (weight * temp0) + ((1 - weight) * meanColor);
                float interpol1 = (weight * temp1) + ((1 - weight) * meanColor);
                float interpol2 = (weight * temp2) + ((1 - weight) * meanColor);
                outColor = vec4(interpol0, interpol1, interpol2, temp3);
            }}
            """

        self.shaderProgram = OpenGL.GL.shaders.compileProgram(
            OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER),
            OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER))

    def drawShape(self, shape, mode=GL_TRIANGLES):
        assert isinstance(shape, es.GPUShape)

        # Binding the proper buffers
        glBindVertexArray(shape.vao)
        glBindBuffer(GL_ARRAY_BUFFER, shape.vbo)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, shape.ebo)
        glBindTexture(GL_TEXTURE_2D, shape.texture)

        # 3d vertices + 2d texture coordinates => 3*4 + 2*4 = 20 bytes
        position = glGetAttribLocation(self.shaderProgram, "position")
        glVertexAttribPointer(position, 3, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(0))
        glEnableVertexAttribArray(position)

        texCoords = glGetAttribLocation(self.shaderProgram, "texCoords")
        glVertexAttribPointer(texCoords, 2, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(12))
        glEnableVertexAttribArray(texCoords)

        # Render the active element buffer with the active shader program
        glDrawElements(mode, shape.size, GL_UNSIGNED_INT, None)

#se obtienen las dimensiones de las ventanas
def setupWindowSize(width, height):
    global WIDTH, HEIGHT
    WIDTH = width
    HEIGHT = height

#se inicializan las animaciones
def setupfinishAnim(lose_image, win_image):
    global MAIN_NODE, BACKGROUND_ANIM, LETTERS_ANIM, WIN_ANIM
    backGround_frames = anim.createFrames(lose_image, [256, 76], [0, 0], [10, 1], [0, 0]) #se recorta la imagen
    letters_frames = anim.createFrames(lose_image, [256, 76], [0, 0], [10, 1], [1, 0]) #se recorta la imagen

    bg_animations = {"appear" : anim.Animation(backGround_frames, 9, False, False)} #se crean las animaciones
    lt_animations = {"appear": anim.Animation(letters_frames, 9, False, False)} #se crean las animaciones

    #Se crean los controladores de las animaciones y se inicializan
    BACKGROUND_ANIM = anim.Anim_Controller(bg_animations, [2, WIDTH / HEIGHT * 1, 1], 0)
    BACKGROUND_ANIM.Play("appear")
    LETTERS_ANIM =  anim.Anim_Controller(lt_animations, [2 * 0.4, WIDTH / HEIGHT * 0.4, 1], 0)
    LETTERS_ANIM.Play("appear")


    win_frames = anim.createFrames(win_image, [128, 192], [0, 0], [2, 11], [0, 0]) #se recorta la imagen
    win_animations = {"appear": anim.Animation(win_frames, 12, False, False)} #se crea la animacion
    # Se crea el controlador de la animacion y se inicializa
    WIN_ANIM = anim.Anim_Controller(win_animations, [2, WIDTH / HEIGHT * 2 * 1.5, 1], 0)
    WIN_ANIM.Play("appear")

#actualiza la animacion de game over
def updateGameOverAnim(delta, pipeline):
    global scale, color
    #modifica el pipeline anterior (el de grafo de escena) a una escala de grises progresivamente
    pipeline.grayScale(color)

    #pipeline para dibujar normalmente la animacion
    temp_pipeline = es.SimpleTextureTransformShaderProgram()
    glUseProgram(temp_pipeline.shaderProgram)
    BACKGROUND_ANIM.Update(temp_pipeline, delta, tr.identity(), False)
    LETTERS_ANIM.Update(temp_pipeline, delta, tr.identity(), False)

    #se vuelve al pipeline anterior
    glUseProgram(pipeline.shaderProgram)

    #efecto de letras crecientes
    if scale < 0.3:
        scale += delta *0.1
    LETTERS_ANIM.scale = [2 * (0.4 + scale), WIDTH / HEIGHT *(0.4 + scale), 1]

    #efecto progresivo de la escala de grises
    if color > 0:
        color -= delta
    else:
        color = 0

#actualiza la animacion de victoria
def updateWinAnim(delta, pipeline):
    WIN_ANIM.Update(pipeline, delta, tr.identity(), False)
