'''
Created on Nov 29, 2020

@author: OSi
'''
from svgwrite import Drawing, rgb
from PIL      import Image


class Vectorize:
    def __init__(self, bitmap, size, width = 0.1, bits = 4, bw = False):
        # Read image
        print('\tVectorizing file ...')
        print('\t\tOpening file ', bitmap)
        bitmap = Image.open(bitmap)
        
        
        # Rescale to be matching to parameters
        factor = min(size[0] / bitmap.size[0] / width,
                     size[1] / bitmap.size[1] / width)
        size   = (size,
                  (int(bitmap.size[0] * factor),
                   int(bitmap.size[1] * factor)))
        
        print('\t\tResizing to: {} x {} : {} ({} x {} mm - F {})'.format(*size[1], width,
                                                                         int(size[1][0] * width),
                                                                         int(size[1][1] * width),
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
                xx = x * width
                moves.append(((x, y), (xx, yy), c))
            
            moves.append(((env[1][1], y), (env[1][1] * width, yy), c))
        
        self.moves = moves
        bitmap.save('/tmp/test.png')



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
    
    
    def save(self):
        with open(self.file, 'w') as f:
            f.write('# Init Marlin Laser code\n')
            
            for i in self.initial:
                f.write('{}\n'.format(i))
            
            
            f.write('\n\n# Engraving code\n')
            
            f.write('G1 X{:.3f} Y{:.3f} F3000 # Move to origin\n'.format(                             self.vectorized.moves[0][1][0],
                                                                         self.vectorized.size[0][1] - self.vectorized.moves[0][1][1]))
            f.write('G1 F{}                # Set burn speed\n\n'.format(self.burn_speed))
            
            print(self.vectorized.size)
            last = self.vectorized.moves[0]
            for i in self.vectorized.moves:
                f.write('G1 ')
                
                if not last[0][0] == i[0][0]:
                    f.write(' X{:.3f}'.format(i[1][0]))
                
                if not last[0][1] == i[0][1]:
                    f.write(' Y{:.3f}'.format(self.vectorized.size[0][1] - i[1][1]))
                
                f.write(' S{}\n'.format(255 - i[2]))
                last = i
            
            
            f.write('\n# Finalize Marlin Laser code\n')
            
            for i in self.final:
                f.write('{}\n'.format(i))



if __name__ == '__main__':
    import click
    
    @click.command()
    @click.option('--input',  '-i', type    = click.Path(exists = True), required = True, help = 'Input bitmap to be vectorized')
    @click.option('--output', '-o', type    = click.Path(),              required = True, help = 'Output G-CODE image')
    @click.option('--svg',    '-v', type    = click.Path(),              default = None,  help = 'Output vectorized SVG image')
    @click.option('--width',  '-w',                                      default  = 100,  help = 'Final image width in mm')
    @click.option('--height', '-h',                                      default  = 100,  help = 'Final image height in mm')
    @click.option('--dot',    '-d', type    = float,                     default  = 0.1,  help = 'Laser path width')
    @click.option('--speed',  '-s', type    = int,                       default  = 1000, help = 'Laser burn speed')
    @click.option('--bits',   '-t',                                      default  = 8,    help = 'Bit resolution of image')
    @click.option('--bw',     '-l', is_flag = True,                                       help = 'Rather use BW instead of grayscale')
    def run(input, output, svg, width, height, dot, speed, bits, bw):
        print('Vectorizing ', input)
        vectorized = Vectorize(input, (width, height), dot, bits, bw)
        
        print('Writing G-CODE to ', output)
        gcode = GCode(output, vectorized, speed)
        gcode.save()
        
        if svg:
            print('Writing SVG graphics to ', svg)
            svg = SvgImage(svg, vectorized)
            svg.save()
        
        print('Done ...')
    
    
    run()