import unittest
from types import SimpleNamespace
from grid_branch_scan import scan_visible_branches

class Array:
    def __init__(self,items):self.items=items;self.Length=len(items)
    def GetElement(self,index):return self.items[index]

class Element:
    def __init__(self,role,name='',children=(),enabled=True,offscreen=False,box=(10,10,100,50)):
        self.CachedControlType=role;self.CachedName=name;self.CachedAutomationId=name
        self.CachedIsEnabled=enabled;self.CachedIsOffscreen=offscreen
        self.CachedBoundingRectangle=SimpleNamespace(left=box[0],top=box[1],right=box[2],bottom=box[3])
        self.children=children;self.calls=0
    def FindAllBuildCache(self,scope,condition,request):
        if scope!=2:raise AssertionError('Only immediate children may be requested')
        self.calls+=1;return Array(self.children)
    def GetCachedPropertyValue(self,prop):return (42,id(self)) if prop==30000 else False

class BranchTests(unittest.TestCase):
    uia=SimpleNamespace(known_control_type_ids={1:'Pane',2:'Button',3:'DataItem',4:'Document'},true_condition=True)
    def scan(self,root):return scan_visible_branches(root,100,200,'app',(0,0,800,600),self.uia,None,1.4)
    def test_disabled_zero_size_host_does_not_hide_enabled_controls(self):
        button=Element(2,'Search')
        host=Element(1,children=[button],enabled=False,box=(0,0,0,0))
        rows=self.scan(Element(1,children=[host]))
        self.assertEqual([r['name'] for r in rows],['Search']);self.assertEqual(host.calls,1)
    def test_chat_items_are_atomic_and_offscreen_items_not_expanded(self):
        hidden=Element(3,'Offscreen',children=[Element(2,'message')],offscreen=True)
        visible=Element(3,'Chat row',children=[Element(2,'message')])
        rows=self.scan(Element(1,children=[hidden,visible]))
        self.assertEqual([r['name'] for r in rows],['Chat row'])
        self.assertEqual(hidden.calls,0);self.assertEqual(visible.calls,0)
    def test_document_descendants_are_discovered_without_full_tree_query(self):
        root=Element(1,children=[Element(4,'Page',children=[Element(2,'New chat')])])
        rows=self.scan(root)
        self.assertIn('New chat',[r['name'] for r in rows]);self.assertEqual(root.calls,1)
    def test_depth_limit_and_disabled_buttons(self):
        nested=Element(2,'Deep')
        for _ in range(25):nested=Element(1,children=[nested])
        rows=self.scan(Element(1,children=[nested,Element(2,'Disabled',enabled=False)]))
        self.assertEqual(rows,[])

if __name__=='__main__':unittest.main()
