from OpenGL.GL import *
import OpenGL.GL.shaders
import numpy as np
import sys

import transformations as tr
import easy_shaders as es
import scene_graph as sg
import basic_shapes as bs
import math
import random

SIZE_IN_BYTES = 4

#Dimensiones de la pantalla que se inician más adelante
WIDTH = 0
HEIGHT = 0

#Clase que hereda SceneGraphNode que contiene la informacion y metodos para detectar colisiones
class CollisionShape(sg.SceneGraphNode):
    def __init__(self, name, radio, canCollide):
        sg.SceneGraphNode.__init__(self, name)
        self.canCollide = canCollide #bool aue indica si puede ser detectado
        self.parent = None #referencia al padre, que es un gameObject
        self.hitbox_radio = radio

    #Funcion que entrega la referencia de un objeto de sceneNode con el que este colisionando, si no detecta colisiones retorna None
    def collidingWith(self, sceneNode):
        #para cada hijo de sceneNode se ve si esta colisionando
        for node in sceneNode.childs:
            targetNodeParent = node #referencia al gameObject
            targetNode = targetNodeParent.childs[1] #referencia al collisionShape
            if targetNode.canCollide: #si el target puede colisionar
                #distancia entre los gameObjects
                tempDist = (self.parent.position[0] - targetNodeParent.position[0])**2 + (HEIGHT/WIDTH*(self.parent.position[1] - targetNodeParent.position[1]))**2
                #Si la distancia entre los objetos es menor que la distancia donde pueden colisionar
                if (tempDist <= (self.hitbox_radio + targetNode.hitbox_radio)**2):
                    return node
        return None

#Se reciben las dimensiones de la ventana
def setupWindowSize(width, height):
    global WIDTH, HEIGHT
    WIDTH = width
    HEIGHT = height

#Pipeline utilizado para dibujar las hitboxes, muestra gpushapes sin texturas y con transparencia
class SimpleTransformShaderProgram:
    def __init__(self):
        vertex_shader = """
            #version 130

            uniform mat4 transform;

            in vec3 position;
            in vec3 color;

            out vec3 newColor;

            void main()
            {
                gl_Position = transform * vec4(position, 1.0f);
                newColor = color;
            }
            """

        fragment_shader = """
            #version 130
            in vec3 newColor;

            out vec4 outColor;

            void main()
            {
                outColor = vec4(newColor, 0.4f);
            }
            """

        self.shaderProgram = OpenGL.GL.shaders.compileProgram(
            OpenGL.GL.shaders.compileShader(vertex_shader, OpenGL.GL.GL_VERTEX_SHADER),
            OpenGL.GL.shaders.compileShader(fragment_shader, OpenGL.GL.GL_FRAGMENT_SHADER))

    def drawShape(self, shape, mode=GL_TRIANGLES):
        assert isinstance(shape, es.GPUShape)

        # Binding the proper buffers
        glBindVertexArray(shape.vao)
        glBindBuffer(GL_ARRAY_BUFFER, shape.vbo)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, shape.ebo)

        # 3d vertices + rgb color specification => 3*4 + 3*4 = 24 bytes
        position = glGetAttribLocation(self.shaderProgram, "position")
        glVertexAttribPointer(position, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(0))
        glEnableVertexAttribArray(position)

        color = glGetAttribLocation(self.shaderProgram, "color")
        glVertexAttribPointer(color, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(12))
        glEnableVertexAttribArray(color)

        # Render the active element buffer with the active shader program
        glDrawElements(mode, shape.size, GL_UNSIGNED_INT, None)

#Crea la GPUShape que representa a la hitbox circular por si se desea mostrar
def createCircleHitbox(radio, sides, r, g, b):
    vertices = [0, 0, 0, r, g, b]
    indices = []

    xt = np.array([radio, 0, 0, 1])
    vertices += [xt[0], xt[1], xt[2], r, g, b]
    indices += [0, 1, 2]

    for i in range(1, sides + 1):
        xtp = np.matmul(tr.rotationZ((2 / sides) * i * np.pi), xt)
        xtr = np.array([xtp[0], xtp[1], xtp[2]]) / xtp[3]

        vertices += [xtr[0], xtr[1], xtr[2], r, g, b]
        if i == (sides):
            indices += [0, i + 1, 1]
        else:
            indices += [0, i + 1, i + 2]

    return bs.Shape(vertices, indices)

