'''
Created on Nov 29, 2020

@author: OSi
'''
from svgwrite import Drawing, rgb
from PIL      import Image


class SvgImage(Drawing):
    def __init__(self, file, size, width):
        print('Creating SVG graphics ...')
        super().__init__(file,
                         size    = size,
                         profile = 'tiny',
                         debug   = True)
        
        self.size  = size
        self.width = width
    
    
    def vectorize(self, bitmap, bw = False, bits = 4):
        # Read image
        print('Vectorizing file ...')
        print('\tOpening file ', bitmap)
        bitmap = Image.open(bitmap)
        
        
        # Rescale to be matching to parameters
        factor = min(self.size[0] / bitmap.size[0] / self.width,
                     self.size[1] / bitmap.size[1] / self.width)
        size   = (int(bitmap.size[0] * factor),
                  int(bitmap.size[1] * factor))
        
        print('\tResizing to: {} x {} : {} ({} x {} mm)'.format(*size,
                                                                self.width,
                                                                int(size[0] * self.width),
                                                                int(size[1] * self.width)))
        bitmap = bitmap.resize(size, Image.LANCZOS)
        bitmap = bitmap.convert('L')
        
        
        # Create BW variant if required
        if bw:
            print('\tConverting to grayscale - BW')
            bitmap = bitmap.convert('1').convert('L')
        
        
        
        # Draw lines
        self['width']  = size[0]
        self['height'] = size[1]
        
        reducto = 2**(8 - bits)
        
        print('\tVectorizing ...')
        for y in range(size[1]):
            if 0 == y % 2:
                env = range(size[0] - 1), 1, 0, size[0] - 2
            else:
                env = reversed(range(1, size[0])), -1, -1, 1
            
            c_begin = -1
            c_cnt   = 1
            p_begin = None
            
            for x in env[0]:
                c = (bitmap.getpixel((x + env[2], y)) // reducto) * reducto
                
                if c_begin < 0:
                    c_begin = c
                
                if c_begin == c and not x == env[3]:
                    if c_cnt == 1:
                        p_begin = x, y
                    c_cnt += 1
                else:
                    if not 255 == c_begin:
                        self.add(self.path('M {} {} h {}'.format(*p_begin, env[1] * c_cnt), stroke = '#000000', stroke_opacity = 1 - c_begin / 255))
                    p_begin = x, y
                    c_cnt   = 1
                    c_begin = c
        
        bitmap.save('/tmp/test.png')


if __name__ == '__main__':
    import click
    
    @click.command()
    @click.option('--input',  '-i', type    = click.Path(exists = True), required = True, help = 'Input bitmap to be vectorized')
    @click.option('--output', '-o', type    = click.Path(),              required = True, help = 'Output vectorized SVG image')
    @click.option('--width',  '-w',                                      default  = 100,  help = 'SVG image width in mm')
    @click.option('--height', '-h',                                      default  = 100,  help = 'SVG image height in mm')
    @click.option('--dot',    '-d', type    = float,                     default  = 0.1,  help = 'Vectorizer path width')
    @click.option('--bits',   '-s',                                      default  = 4,    help = 'Bit resolution of image')
    @click.option('--bw',     '-b', is_flag = True,                                       help = 'Rather use BW instead of grayscale')
    def run(input, output, width, height, dot, bits, bw):
        svg = SvgImage(output, (width, height), dot)
        svg.vectorize(input, bw, bits)
        print('Writing SVG graphics to ', output)
        svg.save()
    
    
    run()