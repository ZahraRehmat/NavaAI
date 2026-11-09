import unittest
from grid_badge_layout import taskbar_layout


def intersects(a,b):
    return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])


class BadgeLayoutTests(unittest.TestCase):
    def item(self,index,x,y,bounds=None):
        return {'label':str(index),'point':(x,y),'bounds':bounds or (x-12,y-16,x+12,y+16),'badge_size':(28,22)}

    def check(self,items,width,height):
        layout=taskbar_layout(items,width,height)
        self.assertEqual(len(layout),len(items))
        for i,item in enumerate(layout):
            l,t,r,b=item['box']
            self.assertTrue(0<=l<r<=width and 0<=t<b<=height)
            self.assertEqual(item['point'],next(original['point'] for original in items if original['label']==item['label']))
            for other in layout[:i]:self.assertFalse(intersects(item['box'],other['box']))
        return layout

    def test_right_tray_dense_and_repeated_anchors_do_not_overlap(self):
        items=[self.item(i,940+(i%3)*14,780) for i in range(18)]
        layout=self.check(items,1000,800)
        self.assertTrue(all(item['box'][3]<764 for item in layout))
        self.assertEqual(layout,taskbar_layout(items,1000,800))

    def test_small_screen_wraps_into_neat_rows(self):
        items=[self.item(i,260+(i%3)*10,280) for i in range(30)]
        layout=self.check(items,320,300)
        self.assertGreater(len({item['box'][1] for item in layout}),1)

    def test_single_narrow_tray_icon_uses_real_bar_orientation(self):
        item=self.item(0,980,780);item['bar_bounds']=(0,750,1000,800)
        placed=self.check([item],1000,800)[0]
        self.assertLess(placed['box'][3],750)

    def test_top_and_vertical_bars_use_inside_screen_rails(self):
        top=[self.item(i,30+i*40,20) for i in range(8)]
        self.assertTrue(all(i['box'][1]>36 for i in self.check(top,800,600)))
        vertical=[self.item(i,780,200+(i%4)*20,bounds=(764,180,800,300)) for i in range(12)]
        self.assertTrue(all(i['box'][2]<764 for i in self.check(vertical,800,600)))

    def test_taskbar_overlay_uses_labels_without_private_or_long_captions(self):
        import tkinter as tk
        from grid_overlay import GridOverlay
        root=tk.Tk();root.withdraw();root.update()
        overlay=GridOverlay(root)
        try:
            cells=[{'label':letter,'scope':'taskbar','name':'Very long privacy microphone notification text '+letter,'bounds':(730+i*10,555,780+i*10,590)} for i,letter in enumerate('AFH')]
            overlay.draw({'active':True,'mode':'smart','config':{'line_color':'cyan','label_color':'yellow','label_background':'black','font_size':9},'areas':[{'monitor':1,'bounds':(0,0,800,600),'cells':cells}]})
            canvas=overlay.canvases[0]
            captions=[canvas.itemcget(i,'text') for i in canvas.find_all() if canvas.type(i)=='text']
            self.assertEqual(captions,list('AFH'))
            boxes=[canvas.bbox(i) for i in canvas.find_all() if canvas.type(i)=='text']
            self.assertTrue(all(box[3]<555 for box in boxes))
        finally:overlay.close();root.destroy()


if __name__=='__main__':unittest.main()
