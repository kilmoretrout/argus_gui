# Argus color palette object
# Contains palettes for use with Matplotlib and Pyglet including color-blind safe palettes for

from __future__ import absolute_import

class ArgusColors():
    def __init__(self):
        self.tableau_color_blind_10 = [(0, 107, 164), (255, 128, 14), (171, 171, 171), (89, 89, 89), (95, 158, 209),
                                       (200, 82, 0), (137, 137, 137), (162, 200, 236), (255, 188, 121), (207, 207, 207)]
        self.color_brewer_qualitative_8_dark = [(228, 26, 28), (55, 126, 184), (77, 175, 74), (152, 78, 163),
                                                (255, 127, 0), (255, 255, 51), (166, 86, 40), (247, 129, 191)]

    def getMatplotlibColors(self):
        colors = self.tableau_color_blind_10

        for i in range(len(colors)):
            r, g, b = colors[i]
            colors[i] = (r / 255., g / 255., b / 255.)

        return colors

    def getPygletColors(self):
        colors = self.color_brewer_qualitative_8_dark

        for i in range(len(colors)):
            r, g, b = colors[i]
            colors[i] = (r, g, b, 255)

        return colors
