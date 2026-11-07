"""Read named targets from an app crop when UIA is incomplete. Local CPU OCR."""
from catalog import norm

def choose_text_target(rows,label):
    from label_matching import choose_label,NoLabelMatch,AmbiguousLabel
    try:return choose_label([r for r in rows if r['score']>=.75],label,key='text')['row']
    except NoLabelMatch:raise ValueError('No visible text matches '+label+'. Nothing was clicked.')
    except AmbiguousLabel as exc:raise ValueError(str(exc)+'. Nothing was clicked.')

class VisualTargets:
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self.engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1)

    def read(self,image):
        import numpy as np
        result,_=self.engine(np.array(image)[:,:,::-1])
        rows=[]
        for box,text,score in result or []:
            xs=[p[0] for p in box]; ys=[p[1] for p in box]
            rows.append({'text':text,'score':float(score),'bounds':[min(xs),min(ys),max(xs),max(ys)]})
        return rows

    def find(self,image,label): return choose_text_target(self.read(image),label)
