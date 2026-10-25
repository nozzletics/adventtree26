nozzletics - Advent Tree 24 (4 tiers x 6 cells, split cells with lip, hidden trays, bayonet post)
4 tiers x 6 = 24 compartments + closed six-segment top with the star

AdventTree_nozzletics.blend   editable model. Text Editor holds the generator scripts:
                              change P{} at the top, Alt+P -> everything rebuilds.
latch.blend                   latch part, separate working file
advent_tree_generator.py      hook variant: cells held by a hook on each tier's post (standalone copy)
advent_tree_mech.py           mech variant: cam drum + 6x3 magnets in a 50 mm tube, builds into AdventTreeMech / ATM_*
advent_tree_motor.py          motor kit for the mech variant (28BYJ-48 stepper + 40x40 speaker), exec'd from advent_tree_mech.py
AdventTree_Drawings.pdf       views, dimensioned section A-A, inventory, assembly (hook variant)
AdventTree_Inventory.csv      part list with sizes and volumes (hook variant)
man_render.py, man_figs.py,   renders the figures of the assembly manual into ../manual
man_steps*.py                 (exec'd inside Blender in this order: man_render, man_figs, man_steps, man_steps2..4)

STL / 3MF exports and renders are not included in this repository: export them from the .blend.

Opening a cell: hook a finger under the overhang, lift ~4.4 mm off the trunk hook and tray, slide out, then pull the two halves apart.
Print a fit test first: T1_C01_A + T1_C01_B + T1_Carrier.

Post joints (base, carriers, top tier): bayonet. Drop the part on (wide lug = one way only), turn 40 deg clockwise seen from above; the ramp pulls it down tight (0.3 mm preload).
Star: two halves back to back, square tapered stem wedges into the tip.

Assembly manual: ../AdventTree_Assembly_Manual.pdf
