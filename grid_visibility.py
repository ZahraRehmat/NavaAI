"""Rectangle subtraction for exposed portions of desktop windows."""
def exposed(box,occluders):
    regions=[tuple(box)]
    for a,b,c,d in occluders:
        remaining=[]
        for l,t,r,bottom in regions:
            x1,y1,x2,y2=max(l,a),max(t,b),min(r,c),min(bottom,d)
            if x1>=x2 or y1>=y2:remaining.append((l,t,r,bottom));continue
            for part in ((l,t,r,y1),(l,y2,r,bottom),(l,y1,x1,y2),(x2,y1,r,y2)):
                if part[2]>part[0] and part[3]>part[1]:remaining.append(part)
        regions=remaining
        if not regions:break
    return regions
