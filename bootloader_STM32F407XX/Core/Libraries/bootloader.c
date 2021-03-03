

#include <bootloader.h>
#include "lwip.h"


uint8_t bootloaderBuffer[BOOTLOADER_BUFFER_LENGTH];

/* Function Prototypes */
static void bootloaderHandle_getVer(uint8_t * bootloaderBuffer);
static void bootloaderHandle_getCid(uint8_t * bootloaderBuffer);
static void bootloaderHandle_getRdp(uint8_t * bootloaderBuffer);
static void bootloaderHandle_setRdp(uint8_t *bootloaderBuffer);
static void bootloaderHandle_go(uint8_t * bootloaderBuffer);
static void bootloaderHandle_flashErase(uint8_t * bootloaderBuffer);
static void bootloaderHandle_enRwProtect(uint8_t * bootloaderBuffer);

static void bootloaderHandle_readSectorProtectionStatus(uint8_t * bootloaderBuffer);
static void bootloaderHandle_readAddressValue(uint8_t * bootloaderBuffer);
static void bootloaderHandle_writeOtpArea(uint8_t * bootloaderBuffer);
static void bootloaderHandle_readOtpStatus(uint8_t *bootloaderBuffer);
static void bootloaderHandle_disRwProtect(uint8_t * bootloaderBuffer);
static void bootloaderHandle_serverConnected(void);

static uint8_t getBootloaderVersion(void);
static uint16_t getMCUChipID(void);
static uint16_t getMCUChipRev(void);
static uint8_t getFlashRdpLevel(void);
static uint8_t setFlashRdpLevel(uint8_t rdpLevel);
static uint8_t verifyAddress(uint32_t checkAddress, verifyAddressOption verifyOption);
static uint8_t executeFlashErase(uint8_t sectorNumber, uint8_t numberOfSectors);

static uint8_t configureFlashSectorRwProtection(uint16_t sectorDetails, uint8_t protectionMode, uint8_t disable);
static uint16_t readOBRwProtectionStatus(void);

static void sendData(uint8_t * pBuffer, uint32_t len);

static void sendNACK(void);
static uint8_t verifyCRC (uint8_t *pData, uint32_t length, uint32_t hostCRC);

/*******************************************************************************************/
/******************** IMPLEMENTATION OF BOOTLOADER JUMPING FUNCTIONS ***********************/
/*******************************************************************************************/

void  bootloaderReadData(void){
 	while(1)
	{
		MX_LWIP_Process();
		switch(bootloaderBuffer[1])
		{
            case BL_GET_VER:
                bootloaderHandle_getVer(bootloaderBuffer);
                memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_GET_CID:
            	bootloaderHandle_getCid(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_GET_RDP_STATUS:
            	bootloaderHandle_getRdp(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_SET_RDP_STATUS:
            	bootloaderHandle_setRdp(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_GO_TO_ADDR:
            	bootloaderHandle_go(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_FLASH_ERASE:
            	bootloaderHandle_flashErase(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_EN_RW_PROTECT:
            	bootloaderHandle_enRwProtect(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_READ_SECTOR_P_STATUS:
            	bootloaderHandle_readSectorProtectionStatus(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_WRITE_OTP_AREA:
            	bootloaderHandle_writeOtpArea(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_READ_OTP_AREA_STATUS:
            	bootloaderHandle_readOtpStatus(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

            case BL_READ_ADDR_VALUE:
            	bootloaderHandle_readAddressValue(bootloaderBuffer);
            	memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

			case BL_DIS_RW_PROTECT:
				bootloaderHandle_disRwProtect(bootloaderBuffer);
				memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

			case BL_SERVER_CONNECTED:
				bootloaderHandle_serverConnected();
				memset(bootloaderBuffer,0,BOOTLOADER_BUFFER_LENGTH);
                break;

             default:
                break;
		}
	}
}

/* Code to jump to user application. We assume that FLASH_SECTOR2_BASE_ADDRESS is where it is stored */
void bootloaderJumpToUserApp(void){
	   //just a function pointer to hold the address of the reset handler of the user app.
	    void (*appResetHandler)(void);

	    // 1. configure the MSP by reading the value from the base address of the sector 4
	    uint32_t mspValue = *(volatile uint32_t *)FLASH_APP_BASE_ADDRESS;

	    //This function comes from CMSIS.
	    __set_MSP(mspValue);
	    //SCB->VTOR = FLASH_SECTOR1_BASE_ADDRESS;
	    /* 2. Now fetch the reset handler address of the user application
	     * from the location FLASH_SECTOR2_BASE_ADDRESS+4
	     */
	    uint32_t resetHandlerAddress = *(volatile uint32_t *) (FLASH_APP_BASE_ADDRESS + 4);

	    appResetHandler = (void*) resetHandlerAddress;

	    //3. jump to reset handler of the user application
	    appResetHandler();

}

/*******************************************************************************************/
/******************** IMPLEMENTATION OF BOOTLOADER COMMAND FUNCTIONS ***********************/
/*******************************************************************************************/

/*Helper function to handle BL_GET_VER command */
static void bootloaderHandle_getVer(uint8_t *bootloaderBuffer) {
	uint8_t blVersionResponse[2] = {0};

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {
		blVersionResponse[0] = BL_GET_VER;
		blVersionResponse[1] = getBootloaderVersion();
		sendData(blVersionResponse, 2);
	} else {
		sendNACK();
	}
}

/*Helper function to handle BL_GET_CID command */
static void bootloaderHandle_getCid(uint8_t *bootloaderBuffer) {
	uint8_t blCidNum[5] = { 0 };

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {
		uint16_t chipID = getMCUChipID();
		uint16_t chipRev = getMCUChipRev();
		blCidNum[0] = BL_GET_CID;
		blCidNum[1] = chipID >> 8;
		blCidNum[2] = chipID;
		blCidNum[3] = chipRev >> 8;
		blCidNum[4] = chipRev;
		sendData((uint8_t*) &blCidNum, 5);
	} else {
		sendNACK();
	}
}

/*Helper function to handle BL_GET_RDP_STATUS command */
static void bootloaderHandle_getRdp(uint8_t *bootloaderBuffer) {
	uint8_t rdpLevel[2] = {0};

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {
		rdpLevel[0] = BL_GET_RDP_STATUS;
		rdpLevel[1] = getFlashRdpLevel();
		sendData(rdpLevel, 2);
	} else {
		sendNACK();
	}
}

/*Helper function to handle BL_SET_RDP_STATUS command */
static void bootloaderHandle_setRdp(uint8_t *bootloaderBuffer) {
	uint8_t rdpLevel[2] = {0};

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {
		rdpLevel[0] = BL_SET_RDP_STATUS;
		rdpLevel[1] = setFlashRdpLevel(bootloaderBuffer[2]);
		sendData(rdpLevel, 2);
	} else {
		sendNACK();
	}
}

 /*Helper function to handle BL_GO_TO_ADDR command */
static void bootloaderHandle_go(uint8_t *bootloaderBuffer) {
	uint32_t goAddress = 0;
	uint8_t addrValidation[2] = {0};

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {
		//Extract the go address
		goAddress = *((uint32_t*) &bootloaderBuffer[2]);
		addrValidation[0] = BL_GO_TO_ADDR;
		if (verifyAddress(goAddress, Go) == ADDR_VALID) {
			//Tell host that address is fine
			addrValidation[1] = ADDR_VALID;
			sendData(addrValidation, 2);

			/*Jump to "go" address.
			 We dont care what is being done there.
			 host must ensure that valid code is present over there
			 Its not the duty of bootloader. so just trust and jump */

			/* Not doing the below line will result in hardfault exception for ARM cortex M */
			//watch : https://www.youtube.com/watch?v=VX_12SjnNhY
			goAddress += 1; //make T bit =1

			void (*jumpToAddress)(void) = (void *)goAddress;

			jumpToAddress();

		} else {
			//Tell host that address is invalid
			addrValidation[1] = ADDR_INVALID;
			sendData(addrValidation, 2);
		}
	} else {
		sendNACK();
	}
}

 /*Helper function to handle BL_FLASH_ERASE command */
static void bootloaderHandle_flashErase(uint8_t * bootloaderBuffer){
	   uint8_t eraseStatus[2] = {0};

		//Total length of the command packet
		uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

		//Extract the CRC32 sent by the Host
		uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

		bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
		if (crcVerification == false) {

#ifdef LED_FLASH_STATUS
	        HAL_GPIO_WritePin(LED_FLASH_PORT, LED_FLASH_PIN, SET);
#endif
	        eraseStatus[0] = BL_FLASH_ERASE;
	        eraseStatus[1] = executeFlashErase(bootloaderBuffer[2] , bootloaderBuffer[3]);
#ifdef LED_FLASH_STATUS
	        HAL_GPIO_WritePin(LED_FLASH_PORT, LED_FLASH_PIN, RESET);
#endif
	        sendData(eraseStatus, 2);
		}
		else{
	        sendNACK();
		}
 }

/*Helper function to handle BL_EN_RW_PROTECT  command */
static void bootloaderHandle_enRwProtect(uint8_t *bootloaderBuffer) {
	uint8_t status[2] = {0};

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {

		status[0] = BL_EN_RW_PROTECT;
		status[1] = configureFlashSectorRwProtection(bootloaderBuffer[3] << 8 | bootloaderBuffer[2], bootloaderBuffer[4], 0);
		sendData(status, 2);
	} else {
		sendNACK();
	}
}

/*Helper function to handle BL_READ_SECTOR_P_STATUS command */
static void bootloaderHandle_readSectorProtectionStatus(uint8_t *bootloaderBuffer) {
	uint8_t status[3] = { 0 };

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {

		status[0] = BL_READ_SECTOR_P_STATUS;
		status[1] = readOBRwProtectionStatus() >> 8;
		status[2] = readOBRwProtectionStatus();
		sendData(status, 3);

	} else {
		sendNACK();
	}
}

 /*Helper function to handle BL_READ_ADDR_VALUE command */
static void bootloaderHandle_readAddressValue(uint8_t * bootloaderBuffer){
	uint8_t status[5] = {0};
	uint32_t readAddress = 0;
	uint32_t readValue = 0;

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {
		status[0]   = BL_READ_ADDR_VALUE;
		readAddress = *((uint32_t*) &bootloaderBuffer[2]);
		if (verifyAddress(readAddress, Read) == ADDR_VALID) {
			readValue   = *((uint32_t*) readAddress);
			status[1]	= ADDR_VALID;
			status[2]   = readValue >> 24;
			status[3]   = readValue >> 16;
			status[4]   = readValue >> 8;
			status[5]   = readValue;
		}
		else {
			status[1]	= ADDR_INVALID;
		}
		sendData(status, 6);
	} else {
		sendNACK();
	}
 }

/*Helper function to handle BL_WRITE_OTP_AREA command */
static void bootloaderHandle_writeOtpArea(uint8_t * bootloaderBuffer){
	uint8_t status[3] = {0};
	uint32_t writeAddress = 0;
	uint32_t writeStatus = 0;


	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {
		status[0]   = BL_WRITE_OTP_AREA;
		writeAddress = *((uint32_t*) &bootloaderBuffer[2]);
		if (verifyAddress(writeAddress, Otp) == ADDR_VALID) {
			HAL_FLASH_Unlock();

			uint32_t writeValue = bootloaderBuffer[6] + (bootloaderBuffer[7] << 8) + (bootloaderBuffer[8] << 16) + (bootloaderBuffer[9] << 24);
			writeStatus = HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, writeAddress,  writeValue);

			HAL_FLASH_Lock();

			status[1]	= ADDR_VALID;
			status[2]	= writeStatus;
		}
		else {
			status[1]	= ADDR_INVALID;
		}
		sendData(status, 6);
	} else {
		sendNACK();
	}
}

/*Helper function to handle BL_READ_OTP_AREA_STATE */
static void bootloaderHandle_readOtpStatus(uint8_t *bootloaderBuffer) {
	uint8_t status[3] = {0};
	uint16_t otpTotalState = 0;
	uint32_t otpBlockState = 0;
	uint32_t * otpAddress = (uint32_t *) OPT_LOCK_BASE;

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {
		status[0]   = BL_READ_OTP_AREA_STATUS;
		uint8_t i = 0;
		for (i = 0; i < 4; i++){
			otpBlockState = *((uint32_t*) (otpAddress + i ));
			uint8_t j = 0;
			for (j = 0; j < 4; j++){
				if( (0xFF & (otpBlockState >> (j * 8))) == RESET){
					otpTotalState |= 0x01 << (4*i + j);
				}
			}

		}
		status[1] = otpTotalState >> 8;
		status[2] = otpTotalState;
		sendData(status, 3);

	} else {
		sendNACK();
	}
}

/*Helper function to handle BL_OTP_READ command */
static void bootloaderHandle_disRwProtect(uint8_t *bootloaderBuffer) {
	uint8_t status[2] = {0};

	//Total length of the command packet
	uint32_t commandPcktLength = bootloaderBuffer[0] + 1;

	//Extract the CRC32 sent by the Host
	uint32_t hostCRC = *((uint32_t*) (bootloaderBuffer + commandPcktLength - 4));

	bool crcVerification = verifyCRC(&bootloaderBuffer[0], commandPcktLength - 4, hostCRC);
	if (crcVerification == false) {

		status[0] = BL_DIS_RW_PROTECT;
		status[1] = configureFlashSectorRwProtection(bootloaderBuffer[3] << 8 | bootloaderBuffer[2], 0, 1);

		sendData(status, 2);
	} else {
		sendNACK();
	}
}

static void bootloaderHandle_serverConnected(void){
	uint8_t ackBuf;
	 ackBuf = BL_ACK;
	 sendData(&ackBuf, 1);
}

static uint8_t getBootloaderVersion(void){
	 return (uint8_t) BL_VERSION;
 }

 //Read the chip identifier or device Identifier
static uint16_t getMCUChipID(void)
 {
 /*
 	The STM32F446xx MCUs integrate an MCU ID code. This ID identifies the ST MCU partnumber
 	and the die revision. It is part of the DBG_MCU component and is mapped on the
 	external PPB bus (see Section 33.16 on page 1304). This code is accessible using the
 	JTAG debug pCat.2ort (4 to 5 pins) or the SW debug port (two pins) or by the user software.
 	It is even accessible while the MCU is under system reset. */
 	uint16_t cid;
 	cid = (uint16_t)(DBGMCU->IDCODE) & 0x0FFF;
 	return  cid;
 }

//Read the revision chip ID
static uint16_t getMCUChipRev(void)
{
	uint16_t cRev;
	cRev = (uint16_t)(((DBGMCU->IDCODE) & 0xFFFF0000) >> 16);
	return  cRev;
}

/*This function reads the RDP ( Read protection option byte) value
 *For more info refer "Table 9. Description of the option bytes" in stm32f407xx RM
 */
static uint8_t getFlashRdpLevel(void){
	uint8_t rdpStatus = 0;
	FLASH_OBProgramInitTypeDef  obHandle;
	HAL_FLASHEx_OBGetConfig(&obHandle);
	rdpStatus = (uint8_t)obHandle.RDPLevel;

	//volatile uint32_t *pOB_addr = (uint32_t*) 0x1FFFC000;
	//rdpStatus =  (uint8_t)(*pOB_addr >> 8);
	return rdpStatus;
}

/*This function sets the RDP ( Read protection option byte) value
 *For more info refer "Table 9. Description of the option bytes" in stm32f407xx RM
 */
static uint8_t setFlashRdpLevel(uint8_t rdpLevel){

	 //Flash option control register (OPTCR)
	volatile uint32_t *pOPTCR = (uint32_t*) 0x40023C14;
	uint8_t status = 0;

	//Option byte configuration unlock
	HAL_FLASH_OB_Unlock();
	//Wait till no active operation on flash
	while(__HAL_FLASH_GET_FLAG(FLASH_FLAG_BSY) != RESET);

	switch(rdpLevel){
					case 0:
						*pOPTCR |= (0xAA << 8);
						//Set the option start bit (OPTSTRT) in the FLASH_OPTCR register
						*pOPTCR |= ( 1 << 1);
						break;
					case 1:
						*pOPTCR |= (0x55 << 8);
						//Set the option start bit (OPTSTRT) in the FLASH_OPTCR register
						*pOPTCR |= ( 1 << 1);
						break;
					case 2:
						*pOPTCR |= (0xCC << 8);
						//Set the option start bit (OPTSTRT) in the FLASH_OPTCR register
						*pOPTCR |= ( 1 << 1);
						break;
					default:
						status = 1;
						break;
	}

	//Wait till no active operation on flash
	while(__HAL_FLASH_GET_FLAG(FLASH_FLAG_BSY) != RESET);
	HAL_FLASH_OB_Lock();

	return status;
}

//Verify the address sent by the host .
static uint8_t verifyAddress(uint32_t checkAddress, verifyAddressOption verifyOption) {

	if (verifyOption == Read)
	{
		if (checkAddress >= FLASH_OTP_BASE && checkAddress <= FLASH_OTP_END) {
			return ADDR_VALID;
		} else if (checkAddress >= CCMDATARAM_BASE && checkAddress <= CCM_RAM_END) {
			return ADDR_VALID;
		} else if (checkAddress >= OTP_AREA_BASE && checkAddress <= OTP_AREA_END) {
			return ADDR_VALID;
		} else if (checkAddress >= OPT_BYTES_BASE && checkAddress <= OPT_BYTES_END) {
			return ADDR_VALID;
		} else if (checkAddress >= FLASH_BASE && checkAddress <= FLASH_END) {
			return ADDR_VALID;
		} else {
			return ADDR_INVALID;
		}
	}
	//so, what are the valid addresses to which we can jump ?
	//can we jump to system memory ? yes
	//can we jump to sram1 memory ?  yes
	//can we jump to sram2 memory ? yes
	//can we jump to backup sram memory ? yes
	//can we jump to peripheral memory ? its possible , but dont allow. so no
	//can we jump to external memory ? yes.

//incomplete -poorly written .. optimize it
	else if (verifyOption == Go)
	{
		if (checkAddress >= SRAM1_BASE && checkAddress <= SRAM1_END) {
			return ADDR_VALID;
		} else if (checkAddress >= SRAM2_BASE && checkAddress <= SRAM2_END) {
			return ADDR_VALID;
		} else if (checkAddress >= FLASH_BASE && checkAddress <= FLASH_END) {
			return ADDR_VALID;
		} else if (checkAddress >= BKPSRAM_BASE && checkAddress <= BKPSRAM_END) {
			return ADDR_VALID;
		} else {
			return ADDR_INVALID;
		}
	}
	else if (verifyOption == Otp){
		if (checkAddress >= OTP_AREA_BASE && checkAddress <= OTP_AREA_END) {
			return ADDR_VALID;
		}
		else {
			return ADDR_INVALID;
		}
	}
	return ADDR_INVALID;
}

static uint8_t executeFlashErase(uint8_t sectorNumber, uint8_t numberOfSectors) {
	//we have totally 12 sectors in STM32F407RE mcu .. sector[0 to 11]
	//numberOfSectors has to be in the range of 0 to 12
	// if sectorNumber = 0xff , that means mass erase !
	FLASH_EraseInitTypeDef flashEraseHandle;
	uint32_t sectorError;
	HAL_StatusTypeDef status;

	if (numberOfSectors > MCU_NUMBER_OF_SECTORS)
		return INVALID_SECTOR;

	if ((sectorNumber == 0xff) || (sectorNumber <= (MCU_NUMBER_OF_SECTORS - 1))) {
		if (sectorNumber == (uint8_t) 0xff) {
			flashEraseHandle.TypeErase = FLASH_TYPEERASE_MASSERASE;
		} else {
			/*Here we are just calculating how many sectors needs to erased */
			uint8_t remaniningSector = MCU_NUMBER_OF_SECTORS - sectorNumber;
			if (numberOfSectors > remaniningSector) {
				numberOfSectors = remaniningSector;
			}
			flashEraseHandle.TypeErase = FLASH_TYPEERASE_SECTORS;
			flashEraseHandle.Sector = sectorNumber; // This is the initial sector
			flashEraseHandle.NbSectors = numberOfSectors;
		}
		flashEraseHandle.Banks = FLASH_BANK_1;

		/*Get access to touch the flash registers */
		HAL_FLASH_Unlock();
		flashEraseHandle.VoltageRange = FLASH_VOLTAGE_RANGE_3; // our mcu will work on this voltage range
		status = (uint8_t) HAL_FLASHEx_Erase(&flashEraseHandle, &sectorError);
		HAL_FLASH_Lock();

		return status;
	}

	return INVALID_SECTOR;
}

/*
 Modifying user option bytes
 To modify the user option value, follow the sequence below:
 1. Check that no Flash memory operation is ongoing by checking the BSY bit in the
 FLASH_SR register
 2. Write the desired option value in the FLASH_OPTCR register.
 3. Set the option start bit (OPTSTRT) in the FLASH_OPTCR register
 4. Wait for the BSY bit to be cleared.
 */
static uint8_t configureFlashSectorRwProtection(uint16_t sectorDetails, uint8_t protectionMode, uint8_t disable) {
	//First configure the protection mode
	//protection_mode =1 , means write protect of the user flash sectors
	//protection_mode =2, means read/write protect of the user flash sectors
	//According to RM of stm32f446xx TABLE 9, We have to modify the address 0x1FFF C008 bit 15(SPRMOD)

	 //Flash option control register (OPTCR)
	volatile uint32_t *pOPTCR = (uint32_t*) 0x40023C14;
	uint8_t status;

	//wait till no active operation on flash
	while (__HAL_FLASH_GET_FLAG(FLASH_FLAG_BSY) != RESET);

	if (disable){
		//disable all r/w protection on sectors
		//Option byte configuration unlock
		HAL_FLASH_OB_Unlock();
		//wait till no active operation on flash
		while(__HAL_FLASH_GET_FLAG(FLASH_FLAG_BSY) != RESET);
		//clear the 31st bit (default state)
		//please refer : Flash option control register (FLASH_OPTCR) in RM
		*pOPTCR &= ~(1 << 31);
		//clear the protection : make all bits belonging to sectors as 1
		*pOPTCR |= (sectorDetails << 16);
		//Set the option start bit (OPTSTRT) in the FLASH_OPTCR register
		*pOPTCR |= ( 1 << 1);
		//wait till no active operation on flash
		while(__HAL_FLASH_GET_FLAG(FLASH_FLAG_BSY) != RESET);
		HAL_FLASH_OB_Lock();
		status = 0;
	}
	else{
		if (protectionMode == 1){
	           //we are putting write protection on the sectors encoded in sector_details argument
				//Option byte configuration unlock
				HAL_FLASH_OB_Unlock();
				//wait till no active operation on flash
				while(__HAL_FLASH_GET_FLAG(FLASH_FLAG_BSY) != RESET);
				//here we are setting just write protection for the sectors
				//clear the 31st bit
				//please refer : Flash option control register (FLASH_OPTCR) in RM
				*pOPTCR &= ~(1 << 31);
				//put write protection on sectors
				*pOPTCR &= ~ (sectorDetails << 16);
				//Set the option start bit (OPTSTRT) in the FLASH_OPTCR register
				*pOPTCR |= ( 1 << 1);
				//wait till no active operation on flash
				while(__HAL_FLASH_GET_FLAG(FLASH_FLAG_BSY) != RESET);
				HAL_FLASH_OB_Lock();
				status = 0;
		}

		else if (protectionMode == 2){
#ifndef STM32F407xx
			HAL_FLASH_OB_Unlock();
			//Flash option control register (OPTCR)
			volatile uint32_t *pOPTCR = (uint32_t*) 0x40023C14;
			//here wer are setting read and write protection for the sectors
			//set the 31st bit
			//please refer : Flash option control register (FLASH_OPTCR) in RM
			*pOPTCR &= ~(1 << 31);   // NOT IN STM32F407
			//put read and write protection on sectors
			*pOPTCR &= ~(0xff << 16);
			*pOPTCR |= (sectorDetails << 16);
			//Set the option start bit (OPTSTRT) in the FLASH_OPTCR register
			*pOPTCR |= (1 << 1);
			//wait till no active operation on flash
			while(__HAL_FLASH_GET_FLAG(FLASH_FLAG_BSY) != RESET);
			HAL_FLASH_OB_Lock();
			status = 0;
#endif
#ifdef STM32F407xx
			status = 1;
#endif
		}
	}
	return status;
}

static uint16_t readOBRwProtectionStatus(void)
{
    //This structure is given by ST Flash driver to hold the OB(Option Byte) contents .
	FLASH_OBProgramInitTypeDef OBInit;

	//First unlock the OB(Option Byte) memory access
	HAL_FLASH_OB_Unlock();
	//get the OB configuration details
	HAL_FLASHEx_OBGetConfig(&OBInit);

	//Get SPRMOD bit (PCROP Protection mode activated)
	OBInit.WRPSector &= 0x7fff;
	OBInit.WRPSector |= ((*(__IO uint8_t *)(OPTCR_BYTE3_ADDRESS)) & 0x80);

	//Lock back .
	HAL_FLASH_Lock();

	//We are just interested in r/w protection status of the sectors.
	return (uint16_t)OBInit.WRPSector;
}

 /* This function writes data in to C_UART */
static void sendData(uint8_t * pBuffer, uint32_t len)
 {
	uint8_t * auxBuffer = malloc(len + 1);
	*auxBuffer = len;
	memcpy(auxBuffer + 1, pBuffer, len);
	udpServer_send(auxBuffer, len + 1);
	free(auxBuffer);
 }

 /*This function sends NACK */
static void sendNACK(void)
 {
 	uint8_t nack = BL_NACK;
 	sendData(&nack, 1);
 }

 /*This verifies the CRC of the given buffer in pData*/
static uint8_t verifyCRC (uint8_t *pData, uint32_t length, uint32_t hostCRC)
 {
     uint32_t uwCRCValue = 0xff;

     for (uint32_t i = 0 ; i < length ; i++)
 	{
         uint32_t iData = pData[i];
         uwCRCValue = HAL_CRC_Accumulate(&hcrc, &iData, 1);
 	}

 	 /* Reset CRC Calculation Unit */
    __HAL_CRC_DR_RESET(&hcrc);

 	if(uwCRCValue == hostCRC)
 	{
 		return VERIFY_CRC_SUCCESS;
 	}

 	return VERIFY_CRC_FAIL;
 }
