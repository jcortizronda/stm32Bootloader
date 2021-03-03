# STM32 Bootloader
Custom bootloader for STM32F4 with application



# STM32 Application
1) Modify linker script to start flash at 0x08010000, with length 960K
2) Modify vector table offset [VECT_TAB_OFFSET] to 0x10000 in system_stm32f4xx.c
