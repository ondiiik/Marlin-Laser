/**
 * Marlin 3D Printer Firmware
 * Copyright (c) 2020 MarlinFirmware [https://github.com/MarlinFirmware/Marlin]
 *
 * Based on Sprinter and grbl.
 * Copyright (c) 2011 Camiel Gubbels / Erik van der Zalm
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 */
#include "../gcode.h"


#if ENABLED(LASER_FEATURE) && HAS_LCD_MENU


#if !defined(LOCATE_SLICE_SIZE)
#define LOCATE_SLICE_SIZE 10.0
#endif


#include "../../feature/spindle_laser.h"
#include "../../module/endstops.h"
#include "../../module/stepper.h"
#include "../../lcd/ultralcd.h"


extern void menu_locate();


namespace
{
    class _Args
    {
    public:
        _Args()
            :
            origin       {               },
            size         {               },
            feedrate     { feedrate_mm_s },
            feedrate_old { feedrate_mm_s },
            laser_power  { 2             }
        {
            const char cidx[] {'X', 'Y', 'I', 'J'};
            float      vals[COUNT(cidx)];
            
            for (auto& c : cidx)
            {
                if (!parser.seenval(c))
                {
                    kill();
                }
                
                vals[&c - cidx] = parser.value_linear_units();
            }
            
            origin.x = vals[0];
            origin.y = vals[1];
            size.x   = vals[2];
            size.y   = vals[3];
            
            float spwr = 2;
            
            if (parser.seen('S'))
            {
                spwr = parser.value_float();
            }
            
            laser_power = TERN(SPINDLE_LASER_PWM, cutter.power_to_range(cutter_power_t(round(spwr))), spwr > 0 ? 255 : 0);
            
            SERIAL_ECHO_MSG("F", parser.linearval('F'));
            if (parser.linearval('F') > 0)
            {
                feedrate = parser.value_feedrate();
                SERIAL_ECHO_MSG("GOT", feedrate);
            }
        }
        
        xy_pos_t   origin;
        xy_pos_t   size;
        feedRate_t feedrate;
        feedRate_t feedrate_old;
        int16_t    laser_power;
    };
    
    
    class _FrameCoro
    {
    public:
        _FrameCoro(const _Args& aArgs)
            :
            _args  { aArgs                     },
            _state { 0                         },
            _end   { aArgs.origin + aArgs.size }
        {
            
        }
        
        
        void operator()()
        {
            _next_loop();
            destination = _dest - position_shift;
            prepare_line_to_destination();
        }
        
        
    private:
        void _next_loop()
        {
            switch (_state)
            {
                // Go to origin
                case 0:
                    _dest             = _args.origin;
                    feedrate_mm_s     = _args.feedrate;
                    cutter.inline_power(_args.laser_power);
                    ++_state;
                    break;
                
                // Move forward in direction X
                case 1:
                {
                    float d { min(_end.x - _dest.x, LOCATE_SLICE_SIZE) };
                    _dest.x += d;
                    
                    if (d < LOCATE_SLICE_SIZE)
                    {
                        planner.synchronize();
                        ++_state;
                    }
                    
                    break;
                }
                
                // Move upward in direction Y
                case 2:
                {
                    float d { min(_end.y - _dest.y, LOCATE_SLICE_SIZE) };
                    _dest.y += d;
                    
                    if (d < LOCATE_SLICE_SIZE)
                    {
                        planner.synchronize();
                        ++_state;
                    }
                    
                    break;
                }
                
                // Move backward in direction X
                case 3:
                {
                    float d { min(_dest.x - _args.origin.x, LOCATE_SLICE_SIZE) };
                    _dest.x -= d;
                    
                    if (d < LOCATE_SLICE_SIZE)
                    {
                        planner.synchronize();
                        ++_state;
                    }
                    
                    break;
                }
                
                // Move downward in direction Y
                case 4:
                {
                    float d { min(_dest.y - _args.origin.y, LOCATE_SLICE_SIZE) };
                    _dest.y -= d;
                    
                    if (d < LOCATE_SLICE_SIZE)
                    {
                        planner.synchronize();
                        _state = 1;
                    }
                    
                    break;
                }
                
                // We shall not appear here 
                default:
                    kill();
            }
        }
        
        const _Args& _args;
        uint8_t      _state;
        xy_pos_t     _end;
        xy_pos_t     _dest;
    };
}


/**
 * G93: Locate area
 */
void GcodeSuite::G93()
{
    /*
     * Activates locate mode and wait till all movements are finished
     */
    planner.synchronize();
    cutter.locate = true;
    ui.defer_status_screen(true);
    ui.goto_screen(menu_locate);
    
    
    /*
     * Get range where to move and create mover coroutine
     */
    _Args      args {      };
    _FrameCoro coro { args };
    
    /*
     * We will move around bounding box till locate mode is exited by user
     */
    while (cutter.locate)
    {
        coro();
        idle();
        endstops.event_handler();
        TERN_(HAS_TFT_LVGL_UI, printer_state_polling());
    }
    
    /*
     * Switch off laser and revert feedrate
     */
    update_workspace_offset(X_AXIS);
    update_workspace_offset(Y_AXIS);
    
    cutter.inline_power(0);
    feedrate_mm_s = args.feedrate_old;
    ui.defer_status_screen(false);
}

#endif
