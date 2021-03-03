/* tftpServer.c for In Application Programming for STM32 Microcontrollers
 * Library by Juan Carlos Ortiz
 */


/***************** Includes ************************/
#include <string.h>
#include <tftpServer.h>
#include "main.h"
#include "flash_if.h"

/***************** Private functions ************************/
static void * openFile(const char * fname, const char * mode, u8_t write);
static void closeFile(void * handle);
static int readFile(void * handle, void * buf, int bytes);
static int writeFile(void * handle, struct pbuf * p);


/******************** Structures ************************/
typedef struct
{
  uint8_t   initFlat;
  uint8_t 	wrMode; // read and write mode 1 write 0 read
  uint32_t  flashAddress ;
}iapFlash_Struct;


const struct tftp_context tftpContext={ //TFTP SERVER docking interface
openFile,
closeFile,
readFile,
writeFile,
};


/***************** Variables ************************/
static  iapFlash_Struct   iapFlashStr ;


/******************** Functions ************************/

  /**
* Open file return file handle
* @param const char* fname filename
   * @param const char* mode
* @param u8_t write mode 1 write 0 read
* @returns file handle
  */
static void* openFile(const char *fname, const char *mode, u8_t write) {
	iapFlashStr.wrMode = write;

	if (iapFlashStr.wrMode == 1) {
		FLASH_If_Init(); //Unlock
		iapFlashStr.flashAddress = USER_FLASH_FIRST_PAGE_ADDRESS; //FLASH start address
		if (FLASH_If_Erase(USER_FLASH_FIRST_PAGE_ADDRESS) == 0) //Erase user area FLASH data
				{
			iapFlashStr.initFlat = 1; //mark initialization is complete
		}
	} //If it is a read file mode
	else if (memcmp(fname, "firmwareSTM32.bin", strlen("firmwareSTM32.bin")) == 0) //Can read internal FLASH
			{
		iapFlashStr.initFlat = 1; //mark initialization is complete
		iapFlashStr.flashAddress = USER_FLASH_FIRST_PAGE_ADDRESS; //FLASH start address
	}
	return (iapFlashStr.initFlat) ? (&iapFlashStr) : NULL; //If the initialization succeeds, return a valid handle
}

  /**
* Close the file handle
   * @param None
   * @param None
   * @param None
   * @returns None
   */
static void closeFile(void *handle) {
	iapFlash_Struct *Filehandle = (iapFlash_Struct*) handle;

	FLASH_If_UnInit(); //FLASH lock
	Filehandle->initFlat = 0;
	if (Filehandle->wrMode) //If the file was previously written
	{
		void (*jumpAddress)(void);

		uint32_t mspValue = *(volatile uint32_t*) USER_FLASH_FIRST_PAGE_ADDRESS;

		//This function comes from CMSIS.
		__set_MSP(mspValue);

		uint32_t jumpToApplication = *(volatile uint32_t*) (FLASH_APP_BASE_ADDRESS + 4);

		jumpAddress = (void*) jumpToApplication;

		//3. jump to reset handler of the user application
		jumpAddress();

		while (1)
			;
	}

}

  /**
* Read file data
* @param handle file handle
* @param *buf Save the cache of data
* @param bytes The length of the data read
* @returns returns the read data length is less than 0 error
   */
static int readFile(void *handle, void *buf, int bytes) {
	iapFlash_Struct *Filehandle = (iapFlash_Struct*) handle;

	if (!Filehandle->initFlat) //not initialized
	{
		return ERR_MEM;
	}
	uint16_t Count;
	for (Count = 0; (Count < bytes) && (Filehandle->flashAddress <= FLASH_END);
			Count++, Filehandle->flashAddress++) {
		((uint8_t*) buf)[Count] = *((__IO uint8_t*) Filehandle->flashAddress);
	}
	return Count;
}


  /**
* Write file data
* @param handle file handle
* @param struct pbuf* p Data cache structure The data cache inside is all the data that needs to be written.
* @returns is less than 0 for error
   */
static int writeFile(void *handle, struct pbuf *p) {
	uint16_t Count;
	iapFlash_Struct *Filehandle = (iapFlash_Struct*) handle;

	if (!Filehandle->initFlat) {

		return ERR_MEM;
	}
	Count = p->len / 4 + ((p->len % 4) > 0); //Get the data to be written

	if (FLASH_If_Write((__IO uint32_t*) &Filehandle->flashAddress,
			(uint32_t*) p->payload, Count) == 0) {

		return ERR_OK;
	} else {

	}
	return ERR_MEM;
}
