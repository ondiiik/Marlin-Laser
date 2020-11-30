'''
Created on Nov 29, 2020

@author: OSi
'''
from svgwrite import Drawing, rgb
from PIL      import Image


class SvgImage(Drawing):
    def __init__(self, file):
        super().__init__(file)
        
#         self.add(self.line((0, 0), (10, 0), stroke = rgb(10, 10, 16, '%')))
        self.add(self.text('Test', insert = (0, 2), fill = 'red'))


if __name__ == '__main__':
    import click
    
    @click.command()
    @click.option('--input',  '-i', type = click.Path(exists = True), required = True, help = 'Input bitmap to be vectorized')
    @click.option('--output', '-o', type = click.Path(),              required = True, help = 'Output vectorized SVG image')
    @click.option('--width',  '-w', type = float,                     default  = 0.1,  help = 'Vectorized path width')
    def run(input, output, width):
        print('Creating SVG graphics ...')
        swg = SvgImage(output)
        print('Writing SVG graphics to ', output)
        swg.save()
    
    
    run()