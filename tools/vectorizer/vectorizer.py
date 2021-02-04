#!/usr/bin/env python
'''
Created on Nov 29, 2020

@author: OSi
'''
#from svgwrite import Drawing, rgb
from PIL import Image


class Vectorize:
    def __init__(self, bitmap, size, width = 0.1, bits = 4, bw = False, file = None):
        # Read image
        print('\tVectorizing file ...')
        print('\t\tOpening file ', bitmap)
        bitmap = Image.open(bitmap)
        
        
        # Rescale to be matching to parameters
        factor = min(size[0] / bitmap.size[0] / width,
                     size[1] / bitmap.size[1] / width)
        size   = ((    bitmap.size[0] * factor * width,
                       bitmap.size[1] * factor * width),
                  (int(bitmap.size[0] * factor),
                   int(bitmap.size[1] * factor)))
        
        print('\t\tResizing to: {} x {} : {} ({:.1f} x {:.1f} mm - F {})'.format(*size[1], width,
                                                                                  size[0][0],
                                                                                  size[0][1],
                                                                                  factor))
        bitmap = bitmap.resize(size[1], Image.LANCZOS)
        bitmap = bitmap.convert('L')
        
        
        # Create BW variant if required
        if bw:
            print('\t\tConverting to grayscale - BW')
            bitmap = bitmap.convert('1').convert('L')
        
        
        
        # Draw lines
        self.size = size
        reducto   = 2**(8 - bits)
        moves     = []
        
        print('\t\tVectorizing ...')
        # Process row
        for y in range(size[1][1]):
            # Optimize for speed - use zig-zag lines
            if 0 == y % 2:
                env = range(1, size[1][0]),           (0, size[1][0])
            else:
                env = reversed(range(1, size[1][0])), (size[1][0], 0)
            
            # Process line
            yy = y * width
            c  = 255
            
            moves.append(((env[1][0], y), (env[1][0] * width, yy), c))
            
            for x in env[0]:
                c  = (bitmap.getpixel((x, y)) // reducto) * reducto
                bitmap.putpixel((x, y), c)
                xx = x * width
                moves.append(((x, y), (xx, yy), c))
            
            moves.append(((env[1][1], y), (env[1][1] * width, yy), c))
        
        
        # Optimize level 2 - merge vertical or horizontal moves
        # with the same intensity
        moves_opt = []
        chunk     = []
        
        for move in moves:
            chunk.append(move)
            
            if len(chunk) < 2:
                continue
            
            if (not chunk[-1][0][0] == chunk[-2][0][0]  or
                not chunk[-1][0][1] == chunk[-2][0][1]) and \
                not chunk[-1][2]    == chunk[-2][2]:
                    moves_opt.append(chunk[-2])
                    chunk = [chunk[-1]]
        
        
        
        self.moves = moves_opt
        
        if file:
            print('Writing PNG bitmap to ', file)
            bitmap.save(file)



class GCode:
    def __init__(self, file, vectorized, speed, marker_cycles, min, max, init_comment = '; Built by vectorizer.py'):
        print('\tCreating G-CODE graphics ...')
        print('\t\tBurn speed {} mm/min'.format(speed))
        self.file          = file
        self.vectorized    = vectorized
        self.initial       = [init_comment,
                              'M05  S0        ; Power laser off',
                              'M300 S440 P150 ; Notify start',
                              'M300 S880 P150',
                              'M300 S440 P150',
                              'M300 S880 P150',
                              'G90            ; Set absolute positioning',
                              'G28            ; Homing' ,
                              'G21            ; Set millimeters',
                              'M400']
        self.final         = ['G1  X0 Y0 S0   ; Home laser head',
                              'M84            ; Disable motors',
                              'M400           ; Wait till moves are finished',
                              'M05 S0         ; Power off laser',
                              'M300 S660 P150 ; Notify end of job',
                              'M300 S1320 P150',
                              'M300 S660 P150',
                              'M300 S1320 P150',
                              'M300 S660 P150',
                              'M300 S1320 P150',
                              'M300 S660 P150',
                              'M300 S1320 P150']
        self.burn_speed    = speed
        self.marker_cycles = marker_cycles
        self.min           = min
        self.rng           = max - min
        self.size_x        = vectorized.size[0][0]
        self.size_y        = vectorized.size[0][1]
    
    
    def save(self):
        with open(self.file, 'w') as f:
            f.write('; Init Marlin Laser code\n')
            
            for i in self.initial:
                f.write('{}\n'.format(i))
            
            f.write('M300 S660 P50\n')
            f.write('M300 S330 P50\n')
            f.write('G93 X{} Y{} I0 J0 F5000 S1 ; Focuss laser\n'.format(self.size_x // 2, self.size_y // 2))
            f.write('M300 S660 P50\n')
            f.write('M300 S330 P50\n')
            f.write('G93 X0 Y0 I{:.3f} J{:.3f} F5000 S1 ; Locate burning area\n'.format(self.size_x, self.size_y))
            
            f.write('\nG1 X0 Y0 S0 F3000 ; Move to origin\n')
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
            
            f.write('G1 X{:.3f} Y{:.3f} F3000 S0 ; Move to origin\n'.format(*self._convert(self.vectorized.moves[0])[0]))
            f.write('G1 F{}                     ; Set burn speed\n\n'.format(self.burn_speed))
            
            last = self._convert(self.vectorized.moves[0])
            
            for i in self.vectorized.moves:
                current = self._convert(i)
                delta   = ((last[0][0] - current[0][0],
                            last[0][1] - current[0][1]),
                            last[1]    - current[1])
                
                if 0 == delta[0][0] and 0 == delta[0][1] and 0 == delta[1]:
                    continue
                
                f.write('G1')
                
                if not 0 == delta[0][0]:
                    f.write(' X{:.3f}'.format(current[0][0]))
                
                if not 0 == delta[0][1]:
                    f.write(' Y{:.3f}'.format(current[0][1]))
                
                f.write(' S{}\n'.format(current[1]))
                last = current
            
            
            f.write('\n; Finalize Marlin Laser code\n')
            
            for i in self.final:
                f.write('{}\n'.format(i))
    
    
    def _convert(self, s):
        intensity = 255 - s[2]
        
        if not 0 == intensity:
            intensity = (intensity * self.rng) // 255 + self.min
        
        return (s[1][0], self.size_y - s[1][1]), intensity 



if __name__ == '__main__':
    import click
    
    @click.command()
    @click.option('--input',  '-i', type    = click.Path(exists = True), required = True, help = 'Input bitmap to be vectorized')
    @click.option('--output', '-o', type    = click.Path(),              required = True, help = 'Output G-CODE image')
    @click.option('--png',    '-p', type    = click.Path(),              default  = None, help = 'Output final PNG image')
    @click.option('--width',  '-w',                                      default  = 100,  help = 'Final image width in mm')
    @click.option('--height', '-h',                                      default  = 100,  help = 'Final image height in mm')
    @click.option('--dot',    '-d', type    = float,                     default  = 0.1,  help = 'Laser path width')
    @click.option('--speed',  '-s', type    = int,                       default  = 1000, help = 'Laser burn speed')
    @click.option('--count',  '-c', type    = int,                       default  = 16,   help = 'Count of low power marker cycles')
    @click.option('--min',    '-m', type    = int,                       default  = 80,   help = 'Minimal non-zero intensity')
    @click.option('--max',    '-x', type    = int,                       default  = 255,  help = 'Maximal intensity')
    @click.option('--bits',   '-t',                                      default  = 8,    help = 'Bit resolution of image')
    @click.option('--bw',     '-l', is_flag = True,                                       help = 'Rather use BW instead of grayscale')
    def run(input, output, png, width, height, dot, speed, count, min, max, bits, bw):
        print('Vectorizing ', input)
        vectorized = Vectorize(input, (width, height), dot, bits, bw, png)
        
        print('Writing G-CODE to ', output)
        gcode = GCode(output, vectorized, speed, count, min, max,
'''; Parameters:
;    vectorizer.input  = {}
;    vectorizer.output = {}
;    vectorizer.png    = {}
;    vectorizer.width  = {}
;    vectorizer.height = {}
;    vectorizer.dot    = {}
;    vectorizer.speed  = {}
;    vectorizer.count  = {}
;    vectorizer.min    = {}
;    vectorizer.max    = {}
;    vectorizer.bits   = {}
;    vectorizer.bw     = {}
'''.format(input, output, png, width, height, dot, speed, count, min, max, bits, bw))
        gcode.save()
        print('Done ...')
    
    
    run()
