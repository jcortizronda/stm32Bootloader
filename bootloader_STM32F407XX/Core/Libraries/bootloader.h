
#include <string.h>
#include <stdbool.h>
#include "main.h"
#include "crc.h"
#include "udpServer.h"
#include "stm32f407xx.h"

#define BL_VERSION 11U	//Version 1.0
#define BOOTLOADER_BUFFER_LENGTH 64

typedef enum
{
	Go = 0,
	Read,
	Otp,
}verifyAddressOption;


// Bootloader Commands

//This command is used to read the bootloader version from the MCU
#define BL_GET_VER				0x51
//This command is used to read the MCU chip identification number and MCU chip revision number
#define BL_GET_CID				0x52
//This command is used to read the FLASH Read Protection level.
#define BL_GET_RDP_STATUS		0x53
//This command is used to jump bootloader to specified address.
#define BL_GO_TO_ADDR			0x54
//This command is used to mass erase or sector erase of the user flash .
#define BL_FLASH_ERASE          0x55
//This command is used to read all the sector protection status.
#define BL_READ_SECTOR_P_STATUS	0x56
//This command is used to enable or disable read/write protect on different sectors of the user flash .
#define BL_EN_RW_PROTECT	    0x57
//This command is used to set the FLASH Read Protection level.
#define BL_SET_RDP_STATUS		0x59
//This command is used to read an address value.
#define BL_READ_ADDR_VALUE		0x58
//This command is used disable all sector read/write protection
#define BL_DIS_RW_PROTECT		0x5C
//This command is used to write data to OTP Area (One Time Programmable Area)
#define BL_WRITE_OTP_AREA		0x5B
//This command is used to read  OTP Area state(One Time Programmable Area)
#define BL_READ_OTP_AREA_STATUS	0x5D
// This command is used to check if the connection can be established between the Client HOST.
#define BL_SERVER_CONNECTED 	BL_ACK
/* USER CODE END Private defines */

/* ADDRESS VALIDATION */
#define ADDR_VALID 0x00
#define ADDR_INVALID 0x01

/*Some Start and End addresses of different memories of STM32F407xx MCU */
/*Change this according to your MCU */
#define SRAM1_SIZE            112*1024     // STM32F446RE has 112KB of SRAM1
#define SRAM1_END             (SRAM1_BASE + SRAM1_SIZE)

#define SRAM2_SIZE            16*1024     // STM32F446RE has 16KB of SRAM2
#define SRAM2_END             (SRAM2_BASE + SRAM2_SIZE)

#define FLASH_SIZE             1024*1024     // STM32F407VGT6 has 1024KB of FLASH

#define BKPSRAM_SIZE           4*1024     // STM32F407VGT6 has 4KB of BACKUP SRAM
#define BKPSRAM_END            (BKPSRAM_BASE + BKPSRAM_SIZE)

#define FLASH_OTP_SIZE			528
#define FLASH_OPT_END			(FLASH_OTP_BASE + FLASH_OTP_SIZE)

#define CCM_RAM_SIZE			64*1024
#define CCM_RAM_END				(CCMDATARAM_BASE + CCM_RAM_SIZE)

#define OTP_AREA_BASE			0x1FFF7800UL
#define OTP_AREA_END			0x1FFF7AFFUL

#define OPT_BYTES_BASE			0x1FFFC000UL
#define OPT_BYTES_END			0x1FFFC00FUL
#define OPT_LOCK_BASE			0x1FFF7A00UL

/* SECTOR VALIDATION */
#define MCU_NUMBER_OF_SECTORS 12 //Number of sectors that MCU has. In case of STM32F407xx is 12 sectors [0...11]
#define INVALID_SECTOR 0x04

/* LED ERASE STATUS*/
#define LED_FLASH_STATUS
#define LED_FLASH_PORT GPIOD
#define LED_FLASH_PIN GPIO_PIN_13

/* ACK and NACK bytes*/
#define BL_ACK   0XA5
#define BL_NACK  0X7F

/*CRC*/
#define VERIFY_CRC_FAIL    1
#define VERIFY_CRC_SUCCESS 0

/* Function Prototypes */
void bootloaderReadData(void);
void bootloaderJumpToUserApp(void);

