'''
Created on Nov 29, 2020

@author: OSi
'''
from svgwrite import Drawing, rgb
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



class SvgImage(Drawing):
    def __init__(self, file, vectorized):
        print('\tCreating SVG graphics ...')
        super().__init__(file,
                         size    = vectorized.size[1],
                         profile = 'tiny',
                         debug   = True)
        
        self.size  = vectorized.size[1]
        
        print('\t\tWriting path ...')
        
        for i in range(len(vectorized.moves) - 1):
            self.add(self.path('M {} {} L {} {}'.format(*vectorized.moves[i][0],
                                                        *vectorized.moves[i + 1][0]),
                               stroke = '#000000',
                               stroke_opacity = 1 - vectorized.moves[i + 1][2] / 255))



class GCode:
    def __init__(self, file, vectorized, speed):
        self.file       = file
        self.vectorized = vectorized
        self.initial    = ['M05 S0   # Power laser off',
                           'G90      # Set absolute positioning',
                           'G28      # Homing' ,
                           'G21      # Set millimeters']
        self.final      = ['M05 I S0 # Power laser off',
                           'G0 X0 Y0 # Park head and invoke laser off']
        self.burn_speed = speed
        self.size_y     = vectorized.size[0][1]
    
    
    def save(self):
        with open(self.file, 'w') as f:
            f.write('# Init Marlin Laser code\n')
            
            for i in self.initial:
                f.write('{}\n'.format(i))
            
            
            f.write('\n\n# Engraving code\n')
            
            f.write('G1 X{:.3f} Y{:.3f} F3000 S0 # Move to origin\n'.format(*self._convert(self.vectorized.moves[0])[0]))
            f.write('G1 F{}                   # Set burn speed\n\n'.format(self.burn_speed))
            
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
                
                if not 0 == delta[1]:
                    f.write(' S{}'.format(current[1]))
                
                f.write('\n')
                last = current
            
            
            f.write('\n# Finalize Marlin Laser code\n')
            
            for i in self.final:
                f.write('{}\n'.format(i))
    
    
    def _convert(self, s):
        return (s[1][0], self.size_y - s[1][1]), 255 - s[2] 



if __name__ == '__main__':
    import click
    
    @click.command()
    @click.option('--input',  '-i', type    = click.Path(exists = True), required = True, help = 'Input bitmap to be vectorized')
    @click.option('--output', '-o', type    = click.Path(),              required = True, help = 'Output G-CODE image')
    @click.option('--png',    '-p', type    = click.Path(),              default  = None, help = 'Output final PNG image')
    @click.option('--svg',    '-v', type    = click.Path(),              default  = None, help = 'Output vectorized SVG image')
    @click.option('--width',  '-w',                                      default  = 100,  help = 'Final image width in mm')
    @click.option('--height', '-h',                                      default  = 100,  help = 'Final image height in mm')
    @click.option('--dot',    '-d', type    = float,                     default  = 0.1,  help = 'Laser path width')
    @click.option('--speed',  '-s', type    = int,                       default  = 1000, help = 'Laser burn speed')
    @click.option('--bits',   '-t',                                      default  = 8,    help = 'Bit resolution of image')
    @click.option('--bw',     '-l', is_flag = True,                                       help = 'Rather use BW instead of grayscale')
    def run(input, output, png, svg, width, height, dot, speed, bits, bw):
        print('Vectorizing ', input)
        vectorized = Vectorize(input, (width, height), dot, bits, bw, png)
        
        print('Writing G-CODE to ', output)
        gcode = GCode(output, vectorized, speed)
        gcode.save()
        
        if svg:
            print('Writing SVG graphics to ', svg)
            svg = SvgImage(svg, vectorized)
            svg.save()
        
        print('Done ...')
    
    
    run()