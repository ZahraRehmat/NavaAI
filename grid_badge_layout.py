"""Compact taskbar callouts, arranged outside the bar instead of over its icons."""

def taskbar_layout(items,width,height,gap=6):
    """Items have bounds, point and badge_size in monitor-local pixels."""
    if not items:return []
    bars=[i.get('bar_bounds',i['bounds']) for i in items]
    left=min(b[0] for b in bars);top=min(b[1] for b in bars)
    right=max(b[2] for b in bars);bottom=max(b[3] for b in bars)
    vertical=bottom-top>right-left
    axis=1 if vertical else 0;limit=height if vertical else width
    ordered=sorted(items,key=lambda item:(item['point'][axis],item['label']))
    groups=[];group=[];used=0
    for item in ordered:
        size=min(limit-2*gap,item['badge_size'][axis])
        if group and used+gap+size>limit-2*gap:groups.append(group);group=[];used=0
        group.append((item,size));used+=size+(gap if used else 0)
    if group:groups.append(group)
    result=[];offset=0
    for group in groups:
        positions=[];end=gap
        for item,size in group:
            position=max(end,min(limit-gap-size,item['point'][axis]-size/2))
            positions.append(position);end=position+size+gap
        end=limit-gap
        for index in reversed(range(len(group))):
            positions[index]=min(positions[index],end-group[index][1])
            end=positions[index]-gap
        thickness=max(item['badge_size'][1-axis] for item,_ in group)
        for (item,size),position in zip(group,positions):
            bw,bh=item['badge_size']
            if vertical:
                x=left-gap-offset-bw if (left+right)/2>width/2 else right+gap+offset
                y=position
            else:
                x=position
                y=top-gap-offset-bh if (top+bottom)/2>height/2 else bottom+gap+offset
            x=max(0,min(width-bw,round(x)));y=max(0,min(height-bh,round(y)))
            result.append({**item,'box':(x,y,x+bw,y+bh)})
        offset+=thickness+gap
    return result
