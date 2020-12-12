#! /usr/bin/env python3
'''
Created on Nov 29, 2020

@author: OSi
'''


class GCode:
    def __init__(self, gcode):
        # Read image
        print('\tReading G-Code ...')
        print('\t\tOpening file ', gcode)
        
        self.file        = gcode
        self.gcode       = []
        self.max_cmd_len = 0
        self.id          = 1
        
        with open(gcode, 'r') as f:
            lines = f.readlines()
            
            for line in lines:
                self.gcode.append(self._parse_line(line.rstrip()))
    
    
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
        
        for cmd in self.gcode:
            g = cmd[0]
            
            if 'G' in g:
                v = g['G']
                
                # Laser burns when extruder runs
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
            
            self._rebuild()
            
            fmt = '{:<' + str(self.max_cmd_len + 4) + '};{}\n'
            
            for cmd in self.gcode:
                if   0 == len(cmd[1]) and 0 == len(cmd[2]):
                    f.write('\n')
                elif 0 == len(cmd[1]):
                    f.write(';{}\n'.format(cmd[2]))
                elif 0 == len(cmd[2]):
                    f.write('{}\n'.format(cmd[1]))
                else:
                    f.write(fmt.format(cmd[1], cmd[2]))
    
    
    def _rebuild(self):
        self.max_cmd_len = 0
        
        for cmd in self.gcode:
            c = cmd[0]
            
            l = ''
            for g in c:
                if not l == '':
                    l += ' '
                l += '{}{}'.format(g[0], c[g[0]])
            
            cmd[1] = l
            self.max_cmd_len = max(self.max_cmd_len, len(l))
    
    
    def _parse_line(self, line):
        cmd = line.split(';', 1)
        
        if 1 == len(cmd):
            cmd.append('')
        
        cmd      = [None, cmd[0], cmd[1], None, self.id]
        self.id += 1
        
        t = cmd[1].split(' ')
        g = {}
        
        for i in t:
            if i == '':
                continue
            
            c = i[0]
            v = i[1:]
            
            if c in 'MGT':
                v = int(v)
            elif not v == '':
                v = float(v)
            else:
                v = None
            
            g[c] = v
        
        cmd[0] = g
        
        self.max_cmd_len = max(self.max_cmd_len, len(cmd[1]))
        return cmd


if __name__ == '__main__':
    def run(input, output):
        print('Converting ', input)
        gcode = GCode(input)
        gcode.prusa2laser()
        
        print('Writing G-CODE to ', output)
        gcode.save(output)
        
        print('Done ...')
    
    
    import sys
    run(sys.argv[1], sys.argv[1])
