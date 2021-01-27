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


#include "../../feature/spindle_laser.h"
#include "../../module/endstops.h"
#include "../../module/stepper.h"
#include "../../lcd/ultralcd.h"


extern void menu_locate();


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
    ui.goto_screen(menu_locate);
    
    /*
     * We will move around bounding box till locate mode is exited by user
     */
    while (cutter.locate)
    {
        idle();
        endstops.event_handler();
        TERN_(HAS_TFT_LVGL_UI, printer_state_polling());
    }
}

#endif
