/**
 * Implementation of 24CW1280T-I/MUY EPROM
 * Author COR
 * Date 27/04/2020
 */

/*
 * Address Upper 1/4 3000h - 3FFFh
 *         Upper 1/2 2000h - 3FFFh
 *         Upper 3/4 1000h - 3FFFh
 *         Entire    0000h - 3FFFh
 */

/* EPROM Capacity 128kbits = 16kBytes
 * page Size 32 Bytes
 * That is, there is 511 pages of 32 Bytes
 */
//-------------------------------------------------------------------------------------------------
// Includes
//-------------------------------------------------------------------------------------------------

#include "Eprom.h"
#include "i2c.h"

//-------------------------------------------------------------------------------------------------
// Directives, typedefs and constants
//-------------------------------------------------------------------------------------------------

#define EPROM	(uint16_t) 0x50
#define PAGE_SIZE	32
#define LAST_page_ADDRESS (0x3FFF - PAGE_SIZE)
#define TIMEOUT 10

#define CONF_REG 0xFFFF  // Configuration Registers {WPR, HAR}
#define HAR_REG_VALUES 0x40  // Default
#define WPR_REG_VALUES 0x46  //Default Values w/o write-protection


//-------------------------------------------------------------------------------------------------
// Function definitions
//-------------------------------------------------------------------------------------------------


u8 Eeprom_ProtectWrite(u8 protectionStatus){
	uint8_t configRegister[2] = { WPR_REG_VALUES, HAR_REG_VALUES };
	switch (protectionStatus) {
	case NoProtect:
		if (EepromWriteData(&I2C_Instance, CONF_REG, configRegister,
				2) != XST_SUCCESS) {
			return XST_FAILURE;
		}
		break;
	case ProtectAll:
		configRegister[0] = 0x4E;
		if (EepromWriteData(&I2C_Instance, CONF_REG, configRegister,
				2) != XST_SUCCESS){
				return XST_FAILURE;
			}
		break;
	default:
		break;
	}
	return XST_SUCCESS;
}

uint16_t Eeprom_Save(uint16_t page, uint8_t *wrteBuffer) {
	u16 ByteCount;
	u16 pageAddress;
	u16 npages = 1;
	if ((ByteCount = strlen(WrteBuffer)) <= PAGE_SIZE) {
		pageAddress = Calc_Address(page);
		EepromWriteData(&I2C_Instance, pageAddress, WrteBuffer, ByteCount);
	} else {
		npages = (ByteCount / PAGE_SIZE) + 1;
		u16 i;
		u16 nBytesLeft;
		for (i = 0; i < npages; i++) {
			pageAddress = Calc_Address(page + i);
			nBytesLeft = ByteCount - i * PAGE_SIZE;
			if (nBytesLeft >= PAGE_SIZE) {
				EepromWriteData(&I2C_Instance, pageAddress,
						WrteBuffer + PAGE_SIZE * i, PAGE_SIZE);
			} else {
				EepromWriteData(&I2C_Instance, pageAddress,
						WrteBuffer + PAGE_SIZE * i, nBytesLeft);
			}
		}
	}
	return npages;
}

uint16_t Eeprom_Load(uint16_t page, uint8_t *readBuffer, uint16_t length) {
	uint16_t pageAddress;
	uint16_t npages = 1;
	pageAddress = Calc_Address(page);
	if (length <= PAGE_SIZE) {
		HAL_I2C_Mem_Read(&hi2c1, EPROM, pageAddress, I2C_MEMADD_SIZE_8BIT, readBuffer, length, TIMEOUT);
	} else {
		npages = (length / PAGE_SIZE) + 1;
		uint16_t i;
		uint16_t nBytesLeft;
		for (i = 0; i < npages; i++) {
			pageAddress = Calc_Address(page + i);
			nBytesLeft = length - i * PAGE_SIZE;
			if (nBytesLeft >= PAGE_SIZE) {
				HAL_I2C_Mem_Read(&hi2c1, EPROM, pageAddress, I2C_MEMADD_SIZE_8BIT, readBuffer + PAGE_SIZE * i, PAGE_SIZE, TIMEOUT);
			} else {
				HAL_I2C_Mem_Read(&hi2c1, EPROM, pageAddress, I2C_MEMADD_SIZE_8BIT, readBuffer + PAGE_SIZE * i, PAGE_SIZE, TIMEOUT);
			}
		}
	}
	return npages;
}

u16 Calc_Address(u16 page) {
	u16 pageAddress;
	pageAddress = page * PAGE_SIZE;
	/* La EPROM tiene 511 paginas de 32 Bytes cada una. La p�gina 512 no existe,
	 *  y debe lanzar error si se quiere escribir/leer sobre ella.
	 *  En este caso, cuando sobrepasa el l�mite, escribe en la �ltima p�gina
	 *  varias veces */
	if (pageAddress > LAST_page_ADDRESS + 1) {
		return LAST_page_ADDRESS;
	}
	return pageAddress;
}

u8 Eeprom_Delete_pages(u16 Initialpage, u16 pagesNumber) {
	u16 i;
	u8 Msg[32] = { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
			0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
			0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
	for (i = Initialpage; i <= (Initialpage + pagesNumber); i++) {
		Eeprom_Save(i, &Msg);
	}
	return XST_SUCCESS;
}


