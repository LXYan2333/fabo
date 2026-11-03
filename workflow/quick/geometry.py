"""Dependency-free molecular stacking shared by QUICK and NWChem probes."""


def stack_geometry(atoms,count,gap):
    """Translate along the thinnest bounding-box axis; keep copies separated."""
    coordinates=[[float(v) for v in atom[1:]] for atom in atoms]
    spans=[max(r[i] for r in coordinates)-min(r[i] for r in coordinates) for i in range(3)]
    axis=min(range(3),key=lambda i:(spans[i],i))
    translation=[0.,0.,0.];translation[axis]=spans[axis]+gap
    lines=[str(len(atoms)*count),f'{count} translated dimers; Angstrom; translation={translation}']
    for copy in range(count):
        for atom,xyz in zip(atoms,coordinates):
            lines.append(atom[0]+' '+ ' '.join(f'{v+copy*t:.12f}' for v,t in zip(xyz,translation)))
    return '\n'.join(lines)+'\n',translation
