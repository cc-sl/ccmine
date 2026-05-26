# -*- coding: utf-8 -*-
'''
基础类定义
包括
1. ThePoint：表示一个点的位置和周围的点
2. self.mine表示一个格子是否有雷
3. self.flag表示一个格子的标记状态，包括无标记、插旗、问号

基本上，ThePoint类包含了一个点的坐标、位置类型
（in、out、left-top、left-bottom、right-top、
right-bottom、left、right、top、bottom）、
是否有雷和标记状态。
通过get_position方法可以获取点的位置类型，
通过get_around方法可以获取周围的点的坐标。

x和y的范围是从0到MAX_WIDTH-1和0到MAX_HEIGHT-1，
x为横坐标，y为纵坐标。
左上角为(0, 0)，右下角为(MAX_WIDTH-1, MAX_HEIGHT-1)。
'''
from config import *
class ThePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.pos = 'in'
        self.mine = False
        self.flag = 'none'
        if x<0 or x>MAX_WIDTH-1 or y<0 or y>MAX_HEIGHT-1:
            self.pos = 'out'
        if x==0 and y==0:
            self.pos = 'left-top'
        if x==0 and y==MAX_HEIGHT-1:
            self.pos = 'left-bottom'
        if x==MAX_WIDTH-1 and y==0:
            self.pos = 'right-top'
        if x==MAX_WIDTH-1 and y==MAX_HEIGHT-1:
            self.pos = 'right-bottom'

        if x==0 and y>0 and y<MAX_HEIGHT-1:
            self.pos = 'left'
        if x==MAX_WIDTH-1 and y>0 and y<MAX_HEIGHT-1:
            self.pos = 'right'
        if y==0 and x>0 and x<MAX_WIDTH-1:
            self.pos = 'top'
        if y==MAX_HEIGHT-1 and x>0 and x<MAX_WIDTH-1:
            self.pos = 'bottom'

    def get_position(self):
        return self.pos

    def get_around(self):
        if self.pos == 'in':
            return [(self.x-1, self.y-1), (self.x, self.y-1), (self.x+1, self.y-1),
                    (self.x-1, self.y),                 (self.x+1, self.y),
                    (self.x-1, self.y+1), (self.x, self.y+1), (self.x+1, self.y+1)] 
        elif self.pos == 'left-top':
            return [(self.x, self.y+1), (self.x+1, self.y), (self.x+1, self.y+1)]
        elif self.pos == 'left-bottom':
            return [(self.x, self.y-1), (self.x+1, self.y), (self.x+1, self.y-1)]
        elif self.pos == 'right-top':
            return [(self.x-1, self.y), (self.x-1, self.y+1), (self.x, self.y+1)]
        elif self.pos == 'right-bottom':
            return [(self.x-1, self.y), (self.x-1, self.y-1), (self.x, self.y-1)]
        elif self.pos == 'left':
            return [(self.x, self.y-1), (self.x+1, self.y-1), (self.x+1, self.y), (self.x+1, self.y+1), (self.x, self.y+1)]
        elif self.pos == 'right':
            return [(self.x-1, self.y-1), (self.x-1, self.y), (self.x-1, self.y+1), (self.x, self.y+1), (self.x, self.y-1)]
        elif self.pos == 'top':
            return [(self.x-1, self.y), (self.x-1, self.y+1), (self.x, self.y+1), (self.x+1, self.y+1), (self.x+1, self.y)]
        elif self.pos == 'bottom':
            return [(self.x-1, self.y), (self.x-1, self.y-1), (self.x, self.y-1), (self.x+1, self.y-1), (self.x+1, self.y)]

if __name__ == "__main__":
    for y in range(-1, MAX_WIDTH+1):
        for x in range(-1, MAX_HEIGHT+1):
            p = ThePoint(x, y)
            print(f"{p.get_position()}",end='\t')
        print()

    