/** \file Eprom.h
 * Header file for Implementation of 24CW1280T-I/MUY EPROM
 * Author COR
 * Date 17/01/2020
 */
#pragma once


//-------------------------------------------------------------------------------------------------
// Includes
//-------------------------------------------------------------------------------------------------

#include <stdio.h>

typedef enum
{
    NoProtect,    // No Data Protection
	ProtectQuarter, // Protect 1/4 First Memory. From 0x
	ProtectHalf,
	ProtectThreeQuarter,
    ProtectAll,   // Protect All Data

} protectionStatus;


//-------------------------------------------------------------------------------------------------
// EEPROM function declarations
//-------------------------------------------------------------------------------------------------

/**
 * brief Eeprom_Save
 * @param Guarda el buffer que se le pasa con el puntero WrteBuffer, en la p�gina solicitada Page. Si el buffer
 * es mayor de 32 bits, ocupa la p�gina siguiente.
 *
 * @return Devuelve el n�mero de p�ginas que se han ocupado al guardar los datos.
 */
u16 Eeprom_Save(u16 Page, u8 *WrteBuffer );


/**
 * brief Eeprom_Load
 * @param Lee los bytes requeridos en el buffer correspondiente y los almacena en el puntero que se le pasa,
 *  en la pagina solicitada. Si el numero de bytes requeridos es mayor de 32, sigue leyendo en las
 *  siguientes paginas, hasta alcanzar el numero de bytes solicitados.
 *
 *  @return HAL_OK or HAL_ERROR
 */
uint16_t Eeprom_Load(uint16_t page, uint8_t *readBuffer, uint16_t length);


/**
 * brief Calc_Address
 * @param Calcula la direcci�n de memoria de la p�gina solicitada.
 *
 * @return pageAddress. La direcci�n correspondiente a la p�gina solicitada.
 */
u16 Calc_Address(u16 Page);


/**
 * brief Eeprom_Delete_Pages
 * @param Reinicia todos los valores de una p�gina, y de las siguientes solicitadas a 0xFF.
 *
 * @return XST SUCCESS
 */
u8 Eeprom_Delete_Pages(u16 InitialPage, u16 PagesNumber);


/**
 * brief Protects the EPROM data
 * @param Bloquea la escritura de la EPROM, por zonas
 *
 */
u8 Eeprom_ProtectWrite(u8 protectionStatus);



