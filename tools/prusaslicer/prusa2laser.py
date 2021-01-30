#! /usr/bin/env python3
'''
Created on Nov 29, 2020

@author: OSi
'''
from gcode import GCode


class PrusaGCode(GCode):
    def __init__(self, gcode):
        # Read image
        print('\tReading G-Code ...')
        print('\t\tOpening file ', gcode)
        super().__init__(gcode)
    
    
    def prusa2laser(self):
        def is_3d_printer(cmd):
            g = cmd[0]
            
            try:
                v = g['M']
                return not v in (82, 106, 107)
            except KeyError:
                pass
            
            try:
                # Remove 3D printer related G-codes
                v = g['G']
                return not v in (92,)
            except KeyError:
                return True
            
            
        # Remove 3D printer related G-codes
        self.gcode = list(filter(is_3d_printer, self.gcode))
        g_moves    = 0, 1, 2, 3, 5
        
        for cmd in self.gcode:
            g = cmd[0]
            
            if 'G' in g:
                v = g['G']
                
                # Laser burns when extruder is active
                if v in g_moves:
                    if 'E' in g:
                        del g['E']
                        if 'X' in g or 'Y' in g:
                            g['S'] = 255
                        else:
                            g['S'] = 0
                    else:
                        g['S'] = 0
            
            if 'Z' in g:
                del g['Z']
    
    
    def save(self, output = None):
        file = output
        
        if not file:
            file = self.file
        
        with open(file, 'w') as f:
            f.write('; Marlin Laser code generated from Prusa Slicer output\n')
            f.write(';     Burn area: ({} - {}) x ({} - {})\n'.format(self.x_min, self.x_max, self.y_min, self.y_max))
            
            self.rebuild()
            
            fmt = '{:<' + str(self.max_cmd_len + 4) + '};{}\n'
            
            for cmd in self.gcode:
                if '@laser_start@' in cmd[2]:
                    f.write('\n\n; Mark area\n')
                    f.write('G93 X{} Y{} I{} J{} F20000 ; Locate burning area\n'.format(self.x_min,
                                                                                        self.y_min,
                                                                                        self.x_max - self.x_min,
                                                                                        self.y_max - self.y_min))
                    
                    f.write('\nG1 X{} Y{} S0 F3000 ; Move to origin\n'.format((self.x_min + self.x_max) // 2, (self.y_min + self.y_max) // 2))
                    f.write('M300 S660 P150      ; Start burning\n')
                    f.write('M300 S1320 P150\n')
                    f.write('M300 S660 P150\n')
                    f.write('M300 S1320 P150\n')
                    for i in range(7):
                        f.write('M300 S660 P150\n')
                        f.write('M300 S1320 P150\n')
                        f.write('M300 S660 P150\n')
                        f.write('M300 S1320 P150\n')
                    f.write('M400\n')
                    f.write('\n\n; Engraving code\n')
                    continue
                
                if   0 == len(cmd[1]) and 0 == len(cmd[2]):
                    f.write('\n')
                elif 0 == len(cmd[1]):
                    f.write(';{}\n'.format(cmd[2]))
                elif 0 == len(cmd[2]):
                    f.write('{}\n'.format(cmd[1]))
                else:
                    f.write(fmt.format(cmd[1], cmd[2]))


if __name__ == '__main__':
    def run(input, output):
        print('Converting ', input)
        gcode = PrusaGCode(input)
        gcode.prusa2laser()
        
        print('Writing G-CODE to ', output)
        gcode.save(output)
        
        print('Done ...')
    
    
    import sys
    run(sys.argv[1], sys.argv[1])
