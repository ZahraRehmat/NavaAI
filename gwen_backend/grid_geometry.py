"""Pixel-exact partitions of physical monitors; independent of AI and UI widgets."""
from dataclasses import dataclass
import re

def column_name(index):
    result='';index+=1
    while index:index,r=divmod(index-1,26);result=chr(65+r)+result
    return result

def column_index(label):
    result=0
    for c in label.upper():result=result*26+ord(c)-64
    return result-1

@dataclass(frozen=True)
class Area:
    monitor:int
    bounds:tuple
    columns:int
    rows:int

    def __post_init__(self):
        l,t,r,b=self.bounds
        if not (r>l and b>t and 1<=self.columns<=r-l and 1<=self.rows<=b-t):raise ValueError('Invalid grid area')

    def cells(self):
        l,t,r,b=self.bounds;w=r-l;h=b-t
        for row in range(self.rows):
            for col in range(self.columns):
                box=(l+col*w//self.columns,t+row*h//self.rows,l+(col+1)*w//self.columns,t+(row+1)*h//self.rows)
                label=f'{column_name(col)}{row+1}'
                yield {'label':label if self.monitor==1 else f'M{self.monitor}-{label}','bounds':box,'point':((box[0]+box[2]-1)//2,(box[1]+box[3]-1)//2),'monitor':self.monitor}

class GridMap:
    def __init__(self,monitors,columns=16,rows=10):
        self.monitors=[tuple(box) for box in monitors];self.columns=columns;self.rows=rows;self.history=[]
        self.reset()

    def reset(self):
        self.areas=[Area(i+1,b,min(self.columns,b[2]-b[0]),min(self.rows,b[3]-b[1])) for i,b in enumerate(self.monitors)];self.history=[]

    def cell(self,label):
        label=re.sub(r'\s+','',label.upper())
        if re.fullmatch(r'[A-Z]+',label):label+='1'
        if label.startswith('M1-'):label=label[3:]
        for area in self.areas:
            for cell in area.cells():
                if cell['label']==label:return cell
        raise ValueError('No grid cell '+label+'. Use a displayed label such as A1 or M2-A1.')

    def locate(self,x,y):
        for area in self.areas:
            for cell in area.cells():
                l,t,r,b=cell['bounds']
                if l<=x<r and t<=y<b:return cell
        return None

    def nearest(self,x,y):
        points=[(max(l,min(r-1,round(x))),max(t,min(b-1,round(y)))) for l,t,r,b in self.monitors]
        return min(points,key=lambda p:(p[0]-x)**2+(p[1]-y)**2)

    def zoom(self,label):
        cell=self.cell(label);l,t,r,b=cell['bounds']
        # Keep cell labels legible. Pixel nudges handle finer positioning.
        cols=min(5,max(1,(r-l)//22));rows=min(5,max(1,(b-t)//20))
        if cols==rows==1:raise ValueError('This is the finest labeled grid here. Use move left/right/up/down 1 or pixel X Y for exact pixels.')
        self.history.append(self.areas);self.areas=[Area(cell['monitor'],cell['bounds'],cols,rows)]

    def back(self):
        if self.history:self.areas=self.history.pop()
        else:self.reset()

    def snapshot(self):return [{'monitor':a.monitor,'bounds':a.bounds,'columns':a.columns,'rows':a.rows,'cells':list(a.cells())} for a in self.areas]
