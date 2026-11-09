"""Small position-aware UIA range fixture; never reads or edits native apps."""
from unittest.mock import Mock


class TextRange:
    def __init__(self,text,left=0,right=None,owner=None):
        self.text=text;self.left=left;self.right=len(text) if right is None else right
        self.owner=owner or self
        if owner is None:self.selected=Mock();self.rectangles=lambda left,right:[]

    def Clone(self):return TextRange(self.text,self.left,self.right,self.owner)
    def GetText(self,limit):return self.text[self.left:self.right][:limit] if limit>=0 else self.text[self.left:self.right]
    def MoveEndpointByRange(self,endpoint,other,other_endpoint):
        value=other.left if other_endpoint==0 else other.right
        if endpoint==0:self.left=value;self.right=max(self.right,value)
        else:self.right=value;self.left=min(self.left,value)
    def MoveEndpointByUnit(self,endpoint,unit,count):
        assert unit==0
        previous=self.left if endpoint==0 else self.right
        value=max(0,min(len(self.text),previous+count))
        if endpoint==0:self.left=value;self.right=max(self.right,value)
        else:self.right=value;self.left=min(self.left,value)
        return value-previous
    def GetBoundingRectangles(self):return self.owner.rectangles(self.left,self.right)
    def Select(self):self.owner.selected(self.left,self.right)
    def FindText(self,*args):raise AssertionError('Character mapping should not need FindText')
