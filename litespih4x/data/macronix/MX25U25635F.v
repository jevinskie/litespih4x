// *============================================================================================== 
// *
// *   MX25U25635F.v - 256M-BIT CMOS Serial Flash Memory
// *
// *           COPYRIGHT 2017 Macronix International Co., Ltd.
// *----------------------------------------------------------------------------------------------
// * Environment  : Cadence NC-Verilog
// * Reference Doc: MX25U25635F REV.1.5,AUG.04,2016
// * Creation Date: @(#)$Date: 2017/05/03 09:05:21 $
// * Version      : @(#)$Revision: 1.16 $
// * Description  : There is only one module in this file
// *                module MX25U25635F->behavior model for the 256M-Bit flash
// *----------------------------------------------------------------------------------------------
// * Note 1:model can load initial flash data from file when parameter Init_File = "xxx" was defined; 
// *        xxx: initial flash data file name;default value xxx = "none", initial flash data is "FF".
// * Note 2:power setup time is tVSL = 1500_000 ns, so after power up, chip can be enable.
// * Note 3:because it is not checked during the Board system simulation the tCLQX timing is not
// *        inserted to the read function flow temporarily.
// * Note 4:more than one values (min. typ. max. value) are defined for some AC parameters in the
// *        datasheet, but only one of them is selected in the behavior model, e.g. program and
// *        erase cycle time is typical value. For the detailed information of the parameters,
// *        please refer to datasheet and contact with Macronix.
// * Note 5:If you have any question and suggestion, please send your mail to following email address :
// *                                    flash_model@mxic.com.tw
// *============================================================================================== 
// * timescale define
// *============================================================================================== 
`timescale 1ns / 100ps

// *============================================================================================== 
// * product parameter define
// *==============================================================================================
        `define MX25U25635FM 16SOP              // RESET#
//      `define MX25U25635FZ 8WSON              // RESET#/SIO3

        `define F133    1'b1                    // 1'b1 for product MX25U25635FZ4I-08G, 1'b0 for other products

    /*----------------------------------------------------------------------*/
    /* all the parameters users may need to change                          */
    /*----------------------------------------------------------------------*/
        `define Vtclqv 6  //30pf:8ns, 15pf:6ns
        `define File_Name         "none"     // Flash data file name for normal array
        `define File_Name_Secu    "none"     // Flash data file name for security region
        `define File_Name_SFDP    "none"     // Flash data file name for SFDP region
        `define VSecur_Reg1_0     2'b00      // security register[1:0]
        `define VSecur_Reg7       1'b0       // security register[7]
        `define VStatus_Reg7_2    6'b0       // status register[7:2] are non-volatile bits
        `define CR_Default4_0     5'b00111      // configuration register default value
        `define VFB_Reg           32'hffff_ffff  // fast boot register

    /*----------------------------------------------------------------------*/
    /* Define controller STATE                                              */
    /*----------------------------------------------------------------------*/
        `define         STANDBY_STATE           0
        `define         CMD_STATE               1
        `define         BAD_CMD_STATE           2
        `define         FAST_BOOT_STATE         3

module MX25U25635F( SCLK, 
                    CS, 
                    SI, 
                    SO, 
                    WP,
`ifdef MX25U25635FM
                    RESET,
`endif
                    SIO3,

                    SI_i, SI_o, SI_oe,
                    SO_i, SO_o, SO_oe,
                    WP_i, WP_o, WP_oe,
                    SIO3_i, SIO3_o, SIO3_oe,

                    );

// *============================================================================================== 
// * Declaration of ports (input, output, inout)
// *============================================================================================== 
    input  SCLK;    // Signal of Clock Input
    input  CS;      // Chip select (Low active)
    inout  SI;      // Serial Input/Output SIO0
    inout  SO;      // Serial Input/Output SIO1
    inout  WP;      // Hardware write protection or Serial Input/Output SIO2
`ifdef MX25U25635FM
    input  RESET;   // Hardware Reset Pin, Active Low
`endif
    inout  SIO3;    // Serial Input/Output SIO3

    input SI_i;
    input SO_i;
    input WP_i;
    input SIO3_i;
    output SI_o;
    output SO_o;
    output WP_o;
    output SIO3_o;
    output SI_oe;
    output SO_oe;
    output WP_oe;
    output SIO3_oe;

// *============================================================================================== 
// * Declaration of parameter (parameter)
// *============================================================================================== 
    /*----------------------------------------------------------------------*/
    /* Density STATE parameter                                              */                  
    /*----------------------------------------------------------------------*/
    parameter   A_MSB           = 24,            
//                 TOP_Add         = 25'h1ffffff,
                TOP_Add         = 25'h1ffff,
                A_MSB_OTP       = 8,                
                Secur_TOP_Add   = 9'h1ff,
                Sector_MSB      = 12,
                A_MSB_SFDP       = 6,
                SFDP_TOP_Add     = 7'h7f,
                Buffer_Num      = 256,
                Block_MSB       = 8,
                Block_NUM       = 512;
  
    /*----------------------------------------------------------------------*/
    /* Define ID Parameter                                                  */
    /*----------------------------------------------------------------------*/
    parameter   ID_MXIC         = 8'hc2,
                ID_Device       = 8'h39,
                Memory_Type     = 8'h25,
                Memory_Density  = 8'h39;

    /*----------------------------------------------------------------------*/
    /* Define Initial Memory File Name                                      */
    /*----------------------------------------------------------------------*/
    parameter   Init_File       = `File_Name;      // initial flash data
    parameter   Init_File_Secu  = `File_Name_Secu; // initial flash data for security
    parameter   Init_File_SFDP  = `File_Name_SFDP;  // initial flash data for SFDP

    /*----------------------------------------------------------------------*/
    /* AC Characters Parameter                                              */
    /*----------------------------------------------------------------------*/
    parameter   tSHQZ           = 8,        // CS High to SO Float Time [ns]
                tCLQV           = `Vtclqv,          // Clock Low to Output Valid
                tCLQX           = 1,        // Output hold time
                tBP             = 12_000,      //  Byte program time
                tSE             = 45_000_000,      // Sector erase time  
                tBE             = 400_000_000,      // Block erase time
                tBE32           = 200_000_000,    // Block 32KB erase time
                tCE             = 200_000,      // unit is ms instead of ns  
                tPP             = 1_000_000,      // Program time
                tW              = 40_000_000,       // Write Status time
                tWREAR          = 40,   // Write extended address register time
                tWRFBR          = 1_000_000,   // Write fast boot register time
                tREADY2_P       = 310_000,  // hardware reset recovery time for pgm
                tREADY2_SE      = 12_000_000,  // hardware reset recovery time for sector ers
                tREADY2_BE      = 25_000_000,  // hardware reset recovery time for block ers
                tREADY2_CE      = 100_000_000,  // hardware reset recovery time for chip ers
                tREADY2_R       = 40_000,  // hardware reset recovery time for read
                tREADY2_D       = 40_000,  // hardware reset recovery time for instruction decoding phase
                tREADY2_W       = 40_000_000,  // hardware reset recovery time for WRSR
                tVSL            = 1500_000;     // Time delay to chip select allowed

    parameter   tESL            = 20_000,       // delay after sector erase suspend command
                tPSL            = 20_000,       // delay after sector program suspend command
                tPRS            = 100_000,      // latency between program resume and next suspend
                tERS            = 200_000;      // latency between erase resume and next suspend

    /*----------------------------------------------------------------------*/
    /* Internal counter parameter                                           */
    /*----------------------------------------------------------------------*/
    parameter  Clock             = 50,      // Internal clock cycle = 100ns
               ERS_Count_BE32K   = tBE32 / (Clock*2) / 500,   // Internal clock cycle = 50us
               ERS_Count_SE      = tSE / (Clock*2) / 500,     // Internal clock cycle = 50us
               ERS_Count_BE      = tBE / (Clock*2) / 500,     // Internal clock cycle = 50us
               Echip_Count       = tCE  / (Clock*2) * 2000; 


    specify
        specparam   tSCLK   = `F133 ? 7.5 : 9.2,    // Clock Cycle Time [ns]
                    fSCLK   = `F133 ? 133 : 108,    // Clock Frequence except READ instruction
                    tRSCLK  = 18.2,   // Clock Cycle Time for READ instruction
                    fRSCLK  = 55,   // Clock Frequence for READ instruction
                    tCH     = `F133 ? 3.3 : 4.5,      // Clock High Time (min) [ns]
                    tCL     = `F133 ? 3.3 : 4.5,      // Clock Low  Time (min) [ns]
                    tCH_R   = 7,      // Clock High Time (min) [ns]
                    tCL_R   = 7,      // Clock Low  Time (min) [ns]
                    tCH_4PP = `F133 ? 3.3 : 4.5,      // Clock High Time (min) [ns]
                    tCL_4PP = `F133 ? 3.3 : 4.5,      // Clock Low  Time (min) [ns]
                    tSLCH   = 5,    // CS# Active Setup Time (relative to SCLK) (min) [ns]
                    tCHSL   = 7,    // CS# Not Active Hold Time (relative to SCLK)(min) [ns]
                    tSHSL_R = 7,    // CS High Time for read instruction (min) [ns]
                    tSHSL_W = 30,    // CS High Time for write instruction (min) [ns]
                    tDVCH   = 4,    // SI Setup Time (min) [ns]
                    tCHDX   = 3,    // SI Hold  Time (min) [ns]
                    tCHSH   = 5,    // CS# Active Hold Time (relative to SCLK) (min) [ns]
                    tSHCH   = 5,    // CS# Not Active Setup Time (relative to SCLK) (min) [ns]
                    tWHSL   = 20,    // Write Protection Setup Time                
                    tSHWL   = 100,    // Write Protection Hold  Time
   
                    tTSCLK  = 11.9,    // Clock Cycle Time for 2XI/O READ instruction
                    tTSCLK2 = 9.2,    // Clock Cycle Time for 2XI/O READ instruction
                    tTSCLK3 = 7.5,    // Clock Cycle Time for 2XI/O READ instruction
                    fTSCLK  = 84,    // Clock Frequence for 2XI/O READ instruction
                    fTSCLK2 = 108,    // Clock Frequence for 2XI/O READ instruction
                    fTSCLK3 = 133,    // Clock Frequence for 2XI/O READ instruction

                    tQSCLK  = 11.9,    // Clock Cycle Time for 4XI/O READ instruction
                    tQSCLK2 = 14.3,    // Clock Cycle Time for 4XI/O READ instruction
                    tQSCLK3 = 9.2,    // Clock Cycle Time for 4XI/O READ instruction
                    tQSCLK4 = 7.5,    // Clock Cycle Time for 4XI/O READ instruction
                    fQSCLK  = 84,    // Clock Frequence for 4XI/O READ instruction
                    fQSCLK2 = 70,  // Clock Frequence for 4XI/O READ instruction
                    fQSCLK3 = 108,  // Clock Frequence for 4XI/O READ instruction
                    fQSCLK4 = 133,  // Clock Frequence for 4XI/O READ instruction

                    tFSCLK   = 9.2,    // Clock Cycle Time for FASTREAD instruction
                    tFSCLK2  = 7.5,    // Clock Cycle Time for FASTREAD instruction
                    fFSCLK   = 108,   // Clock Frequence for FASTREAD instruction
                    fFSCLK2  = 133,   // Clock Frequence for FASTREAD instruction

                    tFDSCLK   = 9.2,    // Clock Cycle Time for DREAD instruction
                    tFDSCLK2  = 7.5,    // Clock Cycle Time for DREAD instruction
                    fFDSCLK   = 108,   // Clock Frequence for DREAD instruction
                    fFDSCLK2  = 133,   // Clock Frequence for DREAD instruction

                    tFQSCLK   = 9.2,    // Clock Cycle Time for QREAD instruction
                    tFQSCLK2  = 11.9,    // Clock Cycle Time for QREAD instruction
                    tFQSCLK3  = 7.5,    // Clock Cycle Time for QREAD instruction
                    fFQSCLK   = 108,    // Clock Frequence for QREAD instruction
                    fFQSCLK2  = 84,   // Clock Frequence for QREAD instruction
                    fFQSCLK3  = 133,   // Clock Frequence for QREAD instruction

                    tFBSCLK   = 14.3,    // Clock Cycle Time for Fast Boot Read 
                    tFBSCLK2  = 11.9,   // Clock Cycle Time for Fast Boot Read 
                    tFBSCLK3  = 9.2,   // Clock Cycle Time for Fast Boot Read 
                    tFBSCLK4  = `F133 ? 7.5 : 9.2,   // Clock Cycle Time for Fast Boot Read
                    fFBSCLK   = 70,    // Clock Frequence for Fast Boot Read 
                    fFBSCLK2  = 84,   // Clock Frequence for Fast Boot Read 
                    fFBSCLK3  = 108,   // Clock Frequence for Fast Boot Read 
                    fFBSCLK4  = `F133 ? 133 : 108,   // Clock Frequence for Fast Boot Read 

                    tRLRH   = 10_000,   // hardware reset pulse
                    tRS     = 15,     // reset setup time
                    tRH     = 15,     // reset hold time
                    tRHSL   = 10_000,  // RESET# high before CS# low
                    tDP     = 10_000,
                    tRES1   = 10_000,
                    tRES2   = 10_000;

     endspecify

    /*----------------------------------------------------------------------*/
    /* Define Command Parameter                                             */
    /*----------------------------------------------------------------------*/
    parameter   WREN        = 8'h06, // WriteEnable   
                WRDI        = 8'h04, // WriteDisable  
                RDSR        = 8'h05, // ReadStatus
                RDCR        = 8'h15, // read configuration register       
                WRSR        = 8'h01, // WriteStatus
                RDID        = 8'h9F, // ReadID
                RES         = 8'hab, // ReadElectricID
                REMS        = 8'h90, // ReadElectricManufacturerDeviceID
                QPIID       = 8'haf, // QPI ID read
                SFDP_READ   = 8'h5a, // enter SFDP read mode
                ENSO        = 8'hb1, // Enter secured OTP;
                EXSO        = 8'hc1, // Exit  secured OTP;
                READ1X      = 8'h03, // ReadData
                READ4B      = 8'h13, // ReadData by 4 byte address
                FASTREAD1X  = 8'h0b, // FastReadData
                FASTREAD4B  = 8'h0c, // FastReadData by 4 byte address
                READ2X      = 8'hbb, // 2X Read
                READ2X4B    = 8'hbc, // 2X Read by 4 byte address
                DREAD       = 8'h3b, // Fastread dual output;
                DREAD4B     = 8'h3c, // Fastread dual output by 4 byte address;
                READ4X      = 8'heb, // 4XI/O Read;
                READ4X_TOP  = 8'hea, // 4XI/O Read start from Top 128Mb;
                READ4X4B    = 8'hec, // 4XI/O Read by 4 byte address;
                QREAD       = 8'h6b, // Fastread quad output;
                QREAD4B     = 8'h6c, // Fastread quad output by 4 byte address;
                PP          = 8'h02, // PageProgram
                PP4B        = 8'h12, // PageProgram by 4 byte address
                FIOPGM0     = 8'h38, // 4I Page Pgm load address and data all 4io
                FIOPGM04B   = 8'h3e, // 4I Page Pgm load address and data all 4io by 4 byte address
                SE          = 8'h20, // SectorErase
                SE4B        = 8'h21, // SectorErase by 4 byte address
                BE32K       = 8'h52, // 32k block erase
                BE32K4B     = 8'h5c, // 32k block erase by 4 byte address
                BE          = 8'hd8, // BlockErase
                BE4B        = 8'hdc, // BlockErase by 4 byte address
                CE1         = 8'h60, // ChipErase
                CE2         = 8'hc7, // ChipErase
                EQIO        = 8'h35, // enable quad I/O
                RSTQIO      = 8'hf5, // reset quad I/O
                EN4B        = 8'hb7, // enter 4-byte mode
                EX4B        = 8'he9, // exit 4-byte mode
                SBL         = 8'hc0, // set burst length
                RDSCUR      = 8'h2b, // Read  security  register;
                WRSCUR      = 8'h2f, // Write security  register;
                RDEAR       = 8'hc8, // Read  extended address register;
                WREAR       = 8'hc5, // Write extended address register;
                RSTEN       = 8'h66, // reset enable
                RST         = 8'h99, // reset memory
                NOP         = 8'h00, // no operation
                DP          = 8'hb9, // DeepPowerDown
                RDP         = 8'hab, // ReleaseFromDeepPowerDown 
                SUSP        = 8'hb0, // write suspend
                RESU        = 8'h30, // write resume
                RDFBR       = 8'h16, // read fast boot register
                WRFBR       = 8'h17, // write fast boot register
                ESFBR       = 8'h18; // erase fast boot register

    /*----------------------------------------------------------------------*/
    /* Declaration of internal-signal                                       */
    /*----------------------------------------------------------------------*/
    reg  [7:0]           ARRAY[0:TOP_Add];  // memory array
    reg  [7:0]           Secur_ARRAY[0:Secur_TOP_Add]; // Secured OTP
    reg  [7:0]           SFDP_ARRAY[0:SFDP_TOP_Add];
    reg  [7:0]           Status_Reg;        // Status Register
    reg  [7:0]           CMD_BUS;
    reg  [31:0]          SI_Reg;            // temp reg to store serial in
    reg  [7:0]           Dummy_A[0:255];    // page size
    reg  [A_MSB:0]       Address;           
    reg  [Sector_MSB:0]  Sector;          
    reg  [Block_MSB:0]   Block;    
    reg  [Block_MSB+1:0] Block2;           
    reg  [2:0]           STATE;

    reg  [7:0]   CR;
    reg  [7:0]           Secur_Reg;         // security register
    reg  [7:0]           EA_Reg;            // extended address register
    reg  [31:0]          FB_Reg;            // Fast Boot register

    reg     SIO0_Reg;
    reg     SIO1_Reg;
    reg     SIO2_Reg;
    reg     SIO3_Reg;
    reg     SIO0_Out_Reg;
    reg     SIO1_Out_Reg;
    reg     SIO2_Out_Reg;
    reg     SIO3_Out_Reg;
    
    reg     Chip_EN;
    reg     DP_Mode;        // deep power down mode
    reg     Read_Mode;
    reg     Read_1XIO_Mode;
    reg     Read_1XIO_Chk;

    reg     FAST_BOOT_Mode;
    reg     FAST_BOOT_Chk;

    reg     tDP_Chk;
    reg     tRES1_Chk;
    reg     tRES2_Chk;

    reg     RDID_Mode;
    reg     RDSR_Mode;
    reg     RDSCUR_Mode;
    reg     RDEAR_Mode;
    reg     RDFBR_Mode;
    reg     FastRD_1XIO_Mode;   
    reg     FastRD_1XIO_Chk;    
    reg     PP_1XIO_Mode;
    reg     SE_4K_Mode;
    reg     BE_Mode;
    reg     BE32K_Mode;
    reg     BE64K_Mode;
    reg     CE_Mode;
    reg     WRSR_Mode;
    reg     WRSR2_Mode;
    reg     WRFBR_Mode;
    reg     ESFBR_Mode;
    reg     RES_Mode;
    reg     REMS_Mode;
    reg     RDCR_Mode;

    reg     EN4B_Mode;

    reg     SCLK_EN;
    reg     SO_OUT_EN;   // for SO
    reg     SI_IN_EN;    // for SI
    reg     SFDP_Mode;
    reg     RST_CMD_EN;
    reg     WRSCUR_Mode;
    reg     WREAR_Mode;
    reg     EN_Burst;
    reg     Susp_Ready;
    reg     Susp_Trig;
    reg     Resume_Trig;
    reg     During_Susp_Wait;
    reg     ERS_CLK;                  // internal clock register for erase timer
    reg     PGM_CLK;                  // internal clock register for program timer
    reg     WR2Susp;

    reg     EN_Boot;
    reg     ADD_4B_Mode;

    wire    CS_INT;
    wire    WP_B_INT;
    wire    RESETB_INT;
    wire    SCLK; 
    wire    WIP;
    wire    ESB;
    wire    PSB;
    wire    EPSUSP;
    wire    WEL;
    wire    SRWD;
    wire    FBE;
    wire    Dis_CE, Dis_WRSR;  
    wire    Norm_Array_Mode;

    wire    Pgm_Mode;
    wire    Ers_Mode;

    event   Resume_Event; 
    event   Susp_Event; 
    event   WRSR_Event; 
    event   WRFBR_Event; 
    event   ESFBR_Event; 
    event   BE_Event;
    event   SE_4K_Event;
    event   CE_Event;
    event   PP_Event;
    event   BE32K_Event;
    event   RST_Event;
    event   RST_EN_Event;
    event   HDRST_Event;

    integer i;
    integer j;
    integer Bit; 
    integer Bit_Tmp; 
    integer Start_Add;
    integer End_Add;
    integer tWRSR;
    integer Burst_Length;
//    time    tRES;
    time    ERS_Time;
    reg Read_SHSL;
    wire Write_SHSL;


    reg     Secur_Mode;     // enter secured mode
    reg     Read_2XIO_Mode;
    reg     Read_2XIO_Chk;
    reg     Byte_PGM_Mode;          
    reg     SI_OUT_EN;   // for SI
    reg     SO_IN_EN;    // for SO
    event   WRSCUR_Event;
    event   WREAR_Event;
   
    reg     Read_4XIO_Mode;
    reg     READ4X_Mode;
    reg     READ4X_TOP_Mode;
    reg     READ4X_BOT_Mode;
    reg     READ4X4B_Mode;
    reg     Read_4XIO_Chk;
    reg     FastRD_2XIO_Mode;
    reg     FastRD_2XIO_Chk;
    reg     FastRD_4XIO_Mode;
    reg     FastRD_4XIO_Chk;
    reg     PP_4XIO_Mode;
    reg     PP_4XIO_Load;
    reg     PP_4XIO_Chk;
    reg     EN4XIO_Read_Mode;
    reg     Set_4XIO_Enhance_Mode;   
    reg     WP_OUT_EN;   // for WP pin
    reg     SIO3_OUT_EN; // for SIO3 pin
    reg     WP_IN_EN;    // for WP pin
    reg     SIO3_IN_EN;  // for SIO3 pin
    reg     ENQUAD;
    reg     During_RST_REC;
    wire    HPM_RD;
    wire    SIO3;
    wire    CR_00;
    wire    CR_01;
    wire    CR_10;
    wire    CR_11;
    assign CR_00 = !CR[7] && !CR[6];
    assign CR_01 = !CR[7] && CR[6];
    assign CR_10 = CR[7] && !CR[6];
    assign CR_11 = CR[7] && CR[6];

    /*----------------------------------------------------------------------*/
    /* initial variable value                                               */
    /*----------------------------------------------------------------------*/
    initial begin
        
        Chip_EN         = 1'b0;
        Secur_Reg       = {`VSecur_Reg7,5'b0_0000,`VSecur_Reg1_0};
        Status_Reg      = {`VStatus_Reg7_2,2'b00};
        CR              = {3'b000,`CR_Default4_0};
        EA_Reg          = 8'b0000_0000;
        FB_Reg  = `VFB_Reg;
        reset_sm;
    end   

    task reset_sm; 
        begin
            During_RST_REC  = 1'b0;
            WRSCUR_Mode     = 1'b0;
            WREAR_Mode     = 1'b0;
            SIO0_Reg        = 1'b1;
            SIO1_Reg        = 1'b1;
            SIO2_Reg        = 1'b1;
            SIO3_Reg        = 1'b1;
            SIO0_Out_Reg    = 1'b1;
            SIO1_Out_Reg    = 1'b1;
            SIO2_Out_Reg    = 1'b1;
            SIO3_Out_Reg    = 1'b1;
            RST_CMD_EN      = 1'b0;
            ENQUAD          = 1'b0;
            SO_OUT_EN       = 1'b0; // SO output enable
            SI_IN_EN        = 1'b0; // SI input enable
            CMD_BUS         = 8'b0000_0000;
            Address         = 0;
            i               = 0;
            j               = 0;
            Bit             = 0;
            Bit_Tmp         = 0;
            Start_Add       = 0;
            End_Add         = 0;
            DP_Mode         = 1'b0;
            SCLK_EN         = 1'b1;
            Read_Mode       = 1'b0;
            Read_1XIO_Mode  = 1'b0;
            Read_1XIO_Chk   = 1'b0;
            tDP_Chk         = 1'b0;
            tRES1_Chk       = 1'b0;
            tRES2_Chk       = 1'b0;

            FAST_BOOT_Mode  = 1'b0;
            FAST_BOOT_Chk  = 1'b0;

            RDID_Mode       = 1'b0;
            RDSR_Mode       = 1'b0;
            RDSCUR_Mode     = 1'b0;
            RDCR_Mode       = 1'b0;
            RDEAR_Mode      = 1'b0;
            RDFBR_Mode      = 1'b0;

            EN4B_Mode = 1'b0;

            PP_1XIO_Mode    = 1'b0;
            SE_4K_Mode      = 1'b0;
            BE_Mode         = 1'b0;
            BE32K_Mode      = 1'b0;
            BE64K_Mode      = 1'b0;
            CE_Mode         = 1'b0;
            WRSR_Mode       = 1'b0;
            WRSR2_Mode      = 1'b0;
            WRFBR_Mode      = 1'b0;
            ESFBR_Mode      = 1'b0;
            RES_Mode        = 1'b0;
            REMS_Mode       = 1'b0;
            Read_SHSL       = 1'b0;
            FastRD_1XIO_Mode  = 1'b0;
            FastRD_1XIO_Chk  = 1'b0;
            FastRD_2XIO_Mode  = 1'b0;
            FastRD_2XIO_Chk  = 1'b0;
            FastRD_4XIO_Mode  = 1'b0;
            FastRD_4XIO_Chk  = 1'b0;
            SI_OUT_EN       = 1'b0; // SI output enable
            SO_IN_EN        = 1'b0; // SO input enable
            Secur_Mode      = 1'b0;
            Read_2XIO_Mode  = 1'b0;
            Read_2XIO_Chk   = 1'b0;
            Byte_PGM_Mode   = 1'b0;
            WP_OUT_EN       = 1'b0; // for WP pin output enable
            SIO3_OUT_EN     = 1'b0; // for SIO3 pin output enable
            WP_IN_EN        = 1'b0; // for WP pin input enable
            SIO3_IN_EN      = 1'b0; // for SIO3 pin input enable
            Read_4XIO_Mode  = 1'b0;

            READ4X4B_Mode    = 1'b0;
            READ4X_Mode    = 1'b0;
            READ4X_TOP_Mode=1'b0;
            READ4X_BOT_Mode=1'b0;

            Read_4XIO_Chk   = 1'b0;
            PP_4XIO_Mode    = 1'b0;
            PP_4XIO_Load    = 1'b0;
            PP_4XIO_Chk     = 1'b0;
            EN4XIO_Read_Mode  = 1'b0;
            Set_4XIO_Enhance_Mode = 1'b0;
            SFDP_Mode = 1'b0;
            EN_Burst          = 1'b0;
            Burst_Length      = 8;
            Susp_Ready        = 1'b1;
            Susp_Trig         = 1'b0;
            Resume_Trig       = 1'b0;
            During_Susp_Wait  = 1'b0;
            ERS_CLK           = 1'b0;
            PGM_CLK           = 1'b0;
            WR2Susp          = 1'b0;

            EN_Boot          = 1'b1;
            ADD_4B_Mode = 1'b0;
        end
    endtask // reset_sm
    
    /*----------------------------------------------------------------------*/
    /* initial flash data                                                   */
    /*----------------------------------------------------------------------*/
    initial 
    begin : memory_initialize
        for ( i = 0; i <=  TOP_Add; i = i + 1 )
            ARRAY[i] = 8'hff; 
        if ( Init_File != "none" )
            $readmemh(Init_File,ARRAY) ;
        for( i = 0; i <=  Secur_TOP_Add; i = i + 1 ) begin
            Secur_ARRAY[i]=8'hff;
        end
        if ( Init_File_Secu != "none" )
            $readmemh(Init_File_Secu,Secur_ARRAY) ;
        for( i = 0; i <=  SFDP_TOP_Add; i = i + 1 ) begin
            SFDP_ARRAY[i] = 8'hff;
        end
        // define SFDP code
        SFDP_ARRAY[8'h0] =  8'h53;
        SFDP_ARRAY[8'h1] =  8'h46;
        SFDP_ARRAY[8'h2] =  8'h44;
        SFDP_ARRAY[8'h3] =  8'h50;
        SFDP_ARRAY[8'h4] =  8'h00;
        SFDP_ARRAY[8'h5] =  8'h01;
        SFDP_ARRAY[8'h6] =  8'h01;
        SFDP_ARRAY[8'h7] =  8'hff;
        SFDP_ARRAY[8'h8] =  8'h00;
        SFDP_ARRAY[8'h9] =  8'h00;
        SFDP_ARRAY[8'ha] =  8'h01;
        SFDP_ARRAY[8'hb] =  8'h09;
        SFDP_ARRAY[8'hc] =  8'h30;
        SFDP_ARRAY[8'hd] =  8'h00;
        SFDP_ARRAY[8'he] =  8'h00;
        SFDP_ARRAY[8'hf] =  8'hff;
        SFDP_ARRAY[8'h10] =  8'hc2;
        SFDP_ARRAY[8'h11] =  8'h00;
        SFDP_ARRAY[8'h12] =  8'h01;
        SFDP_ARRAY[8'h13] =  8'h04;
        SFDP_ARRAY[8'h14] =  8'h60;
        SFDP_ARRAY[8'h15] =  8'h00;
        SFDP_ARRAY[8'h16] =  8'h00;
        SFDP_ARRAY[8'h17] =  8'hff;
        SFDP_ARRAY[8'h18] =  8'hff;
        SFDP_ARRAY[8'h19] =  8'hff;
        SFDP_ARRAY[8'h1a] =  8'hff;
        SFDP_ARRAY[8'h1b] =  8'hff;
        SFDP_ARRAY[8'h1c] =  8'hff;
        SFDP_ARRAY[8'h1d] =  8'hff;
        SFDP_ARRAY[8'h1e] =  8'hff;
        SFDP_ARRAY[8'h1f] =  8'hff;
        SFDP_ARRAY[8'h20] =  8'hff;
        SFDP_ARRAY[8'h21] =  8'hff;
        SFDP_ARRAY[8'h22] =  8'hff;
        SFDP_ARRAY[8'h23] =  8'hff;
        SFDP_ARRAY[8'h24] =  8'hff;
        SFDP_ARRAY[8'h25] =  8'hff;
        SFDP_ARRAY[8'h26] =  8'hff;
        SFDP_ARRAY[8'h27] =  8'hff;
        SFDP_ARRAY[8'h28] =  8'hff;
        SFDP_ARRAY[8'h29] =  8'hff;
        SFDP_ARRAY[8'h2a] =  8'hff;
        SFDP_ARRAY[8'h2b] =  8'hff;
        SFDP_ARRAY[8'h2c] =  8'hff;
        SFDP_ARRAY[8'h2d] =  8'hff;
        SFDP_ARRAY[8'h2e] =  8'hff;
        SFDP_ARRAY[8'h2f] =  8'hff;
        SFDP_ARRAY[8'h30] =  8'he5;
        SFDP_ARRAY[8'h31] =  8'h20;
        SFDP_ARRAY[8'h32] =  8'hf3;
        SFDP_ARRAY[8'h33] =  8'hff;
        SFDP_ARRAY[8'h34] =  8'hff;
        SFDP_ARRAY[8'h35] =  8'hff;
        SFDP_ARRAY[8'h36] =  8'hff;
        SFDP_ARRAY[8'h37] =  8'h0f;
        SFDP_ARRAY[8'h38] =  8'h44;
        SFDP_ARRAY[8'h39] =  8'heb;
        SFDP_ARRAY[8'h3a] =  8'h08;
        SFDP_ARRAY[8'h3b] =  8'h6b;
        SFDP_ARRAY[8'h3c] =  8'h08;
        SFDP_ARRAY[8'h3d] =  8'h3b;
        SFDP_ARRAY[8'h3e] =  8'h04;
        SFDP_ARRAY[8'h3f] =  8'hbb;
        SFDP_ARRAY[8'h40] =  8'hfe;
        SFDP_ARRAY[8'h41] =  8'hff;
        SFDP_ARRAY[8'h42] =  8'hff;
        SFDP_ARRAY[8'h43] =  8'hff;
        SFDP_ARRAY[8'h44] =  8'hff;
        SFDP_ARRAY[8'h45] =  8'hff;
        SFDP_ARRAY[8'h46] =  8'h00;
        SFDP_ARRAY[8'h47] =  8'hff;
        SFDP_ARRAY[8'h48] =  8'hff;
        SFDP_ARRAY[8'h49] =  8'hff;
        SFDP_ARRAY[8'h4a] =  8'h44;
        SFDP_ARRAY[8'h4b] =  8'heb;
        SFDP_ARRAY[8'h4c] =  8'h0c;
        SFDP_ARRAY[8'h4d] =  8'h20;
        SFDP_ARRAY[8'h4e] =  8'h0f;
        SFDP_ARRAY[8'h4f] =  8'h52;
        SFDP_ARRAY[8'h50] =  8'h10;
        SFDP_ARRAY[8'h51] =  8'hd8;
        SFDP_ARRAY[8'h52] =  8'h00;
        SFDP_ARRAY[8'h53] =  8'hff;
        SFDP_ARRAY[8'h54] =  8'hff;
        SFDP_ARRAY[8'h55] =  8'hff;
        SFDP_ARRAY[8'h56] =  8'hff;
        SFDP_ARRAY[8'h57] =  8'hff;
        SFDP_ARRAY[8'h58] =  8'hff;
        SFDP_ARRAY[8'h59] =  8'hff;
        SFDP_ARRAY[8'h5a] =  8'hff;
        SFDP_ARRAY[8'h5b] =  8'hff;
        SFDP_ARRAY[8'h5c] =  8'hff;
        SFDP_ARRAY[8'h5d] =  8'hff;
        SFDP_ARRAY[8'h5e] =  8'hff;
        SFDP_ARRAY[8'h5f] =  8'hff;
        SFDP_ARRAY[8'h60] =  8'h00;
        SFDP_ARRAY[8'h61] =  8'h20;
        SFDP_ARRAY[8'h62] =  8'h50;
        SFDP_ARRAY[8'h63] =  8'h16;
        SFDP_ARRAY[8'h64] =  8'h9d;
        SFDP_ARRAY[8'h65] =  8'hf9;
        SFDP_ARRAY[8'h66] =  8'hc0;
        SFDP_ARRAY[8'h67] =  8'h64;
        SFDP_ARRAY[8'h68] =  8'hfe;
        SFDP_ARRAY[8'h69] =  8'hcf;
        SFDP_ARRAY[8'h6a] =  8'hff;
        SFDP_ARRAY[8'h6b] =  8'hff;
        SFDP_ARRAY[8'h6c] =  8'hff;
        SFDP_ARRAY[8'h6d] =  8'hff;
        SFDP_ARRAY[8'h6e] =  8'hff;
        SFDP_ARRAY[8'h6f] =  8'hff;
    end

// *============================================================================================== 
// * Input/Output bus operation 
// *============================================================================================== 
    assign   CS_INT = ( During_RST_REC == 1'b0 && RESETB_INT == 1'b1 && Chip_EN ) ? CS : 1'b1;
    assign WP_B_INT = (Status_Reg[6] == 1'b0 && ENQUAD == 1'b0) ? WP : 1'b1;
    assign   SO     = SO_OUT_EN ? SIO1_Out_Reg : 1'bz ;
    assign   SI     = SI_OUT_EN ? SIO0_Out_Reg : 1'bz ;
    assign   WP     = WP_OUT_EN   ? SIO2_Out_Reg : 1'bz ;
    assign   SIO3   = SIO3_OUT_EN ? SIO3_Out_Reg : 1'bz ;
`ifdef MX25U25635FM
    assign   RESETB_INT = (RESET === 1'b1 || RESET === 1'b0) ? RESET : 1'b1;
`endif
`ifdef MX25U25635FZ
    assign   RESETB_INT = (Status_Reg[6] == 1'b0 && ENQUAD == 1'b0)? ((SIO3 === 1'b1 || SIO3 === 1'b0) ? SIO3 : 1'b1): 1'b1;
`endif

    /*----------------------------------------------------------------------*/
    /* output buffer                                                        */
    /*----------------------------------------------------------------------*/
    always @( SIO3_Reg or SIO2_Reg or SIO1_Reg or SIO0_Reg ) begin
        if ( SIO3_OUT_EN && WP_OUT_EN && SO_OUT_EN && SI_OUT_EN ) begin
            SIO3_Out_Reg <= #tCLQV SIO3_Reg;
            SIO2_Out_Reg <= #tCLQV SIO2_Reg;
            SIO1_Out_Reg <= #tCLQV SIO1_Reg;
            SIO0_Out_Reg <= #tCLQV SIO0_Reg;
        end
        else if ( SO_OUT_EN && SI_OUT_EN ) begin
            SIO1_Out_Reg <= #tCLQV SIO1_Reg;
            SIO0_Out_Reg <= #tCLQV SIO0_Reg;
        end
        else if ( SO_OUT_EN ) begin
            SIO1_Out_Reg <= #tCLQV SIO1_Reg;
        end
    end

// *============================================================================================== 
// * Finite State machine to control Flash operation
// *============================================================================================== 
    /*----------------------------------------------------------------------*/
    /* power on                                                             */
    /*----------------------------------------------------------------------*/
    initial begin 
        Chip_EN   <= #tVSL 1'b1;// Time delay to chip select allowed 
    end
    
    /*----------------------------------------------------------------------*/
    /* Command Decode                                                       */
    /*----------------------------------------------------------------------*/
    assign ESB      = Secur_Reg[3] ;
    assign PSB      = Secur_Reg[2] ;
    assign EPSUSP   = ESB | PSB ;
    assign WIP      = Status_Reg[0] ;
    assign WEL      = Status_Reg[1] ;
    assign SRWD     = Status_Reg[7] ;
    assign Dis_CE   = Status_Reg[5] == 1'b1 || Status_Reg[4] == 1'b1 ||
                      Status_Reg[3] == 1'b1 || Status_Reg[2] == 1'b1;
    assign HPM_RD   = EN4XIO_Read_Mode == 1'b1 ;  
    assign Norm_Array_Mode = ~Secur_Mode;
    assign Dis_WRSR = (WP_B_INT == 1'b0 && Status_Reg[7] == 1'b1) || (!Norm_Array_Mode);
    assign Pgm_Mode = PP_1XIO_Mode || PP_4XIO_Mode;
    assign Ers_Mode = SE_4K_Mode || BE_Mode;

    assign FBE       = FB_Reg[0];

    always @ ( negedge CS_INT ) begin
        if ( !EN_Boot || FBE ) begin
            SI_IN_EN = 1'b1;
        end 
        if ( ENQUAD ) begin
            SO_IN_EN    = 1'b1;
            SI_IN_EN    = 1'b1;
            WP_IN_EN    = 1'b1;
            SIO3_IN_EN  = 1'b1;
        end
        if ( EN4XIO_Read_Mode == 1'b1 ) begin
            //$display( $time, " Enter READX4 Function ..." );
            Read_SHSL = 1'b1;
            STATE   <= `CMD_STATE;
            Read_4XIO_Mode = 1'b1; 
        end
        if ( HPM_RD == 1'b0 ) begin
            Read_SHSL <= #1 1'b0;   
        end
        #1;
        tDP_Chk = 1'b0;
        tRES1_Chk = 1'b0;
        tRES2_Chk = 1'b0;
    end


    always @ ( posedge SCLK or posedge CS_INT ) begin
        #0;  
        if ( CS_INT == 1'b0 ) begin
            if ( ENQUAD ) begin
                Bit_Tmp = Bit_Tmp + 4;
                Bit     = Bit_Tmp - 1;
            end
            else begin
                Bit_Tmp = Bit_Tmp + 1;
                Bit     = Bit_Tmp - 1;
            end
            if ( SI_IN_EN == 1'b1 && SO_IN_EN == 1'b1 && WP_IN_EN == 1'b1 && SIO3_IN_EN == 1'b1 ) begin
                SI_Reg[31:0] = ( CR[5] || ADD_4B_Mode ) ? {SI_Reg[27:0], SIO3, WP, SO, SI} : {8'b0, SI_Reg[19:0], SIO3, WP, SO, SI};
            end 
            else  if ( SI_IN_EN == 1'b1 && SO_IN_EN == 1'b1 ) begin
                SI_Reg[31:0] = ( CR[5] || ADD_4B_Mode ) ? {SI_Reg[29:0], SO, SI} : {8'b0, SI_Reg[21:0], SO, SI};
            end
            else if ( SI_IN_EN == 1'b1 ) begin 
                SI_Reg[31:0] = ( CR[5] || ADD_4B_Mode ) ? {SI_Reg[30:0], SI} : {8'b0, SI_Reg[22:0], SI};
            end

            if ( (EN4XIO_Read_Mode == 1'b1 && ((Bit == 5 && !ENQUAD && !CR[5] && !ADD_4B_Mode ) || (Bit == 23 && ENQUAD && !CR[5] && !ADD_4B_Mode ))) ) begin
                Address = SI_Reg[A_MSB:0];
                if ( READ4X_TOP_Mode == 1'b1 )
                        Address [24] = 1'b1;
                else
                        Address [24] = EA_Reg[0];
                load_address(Address);
            end
            else if ( (EN4XIO_Read_Mode == 1'b1 && ((Bit == 7 && !ENQUAD && ( CR[5] || ADD_4B_Mode )) || (Bit == 31 && ENQUAD && ( CR[5] || ADD_4B_Mode )))) ) begin
                Address = SI_Reg[A_MSB:0];
                load_address(Address);
            end  
        end     
  
        if ( Bit == 7 && CS_INT == 1'b0 && ~HPM_RD && ( !EN_Boot || FBE ) ) begin
            STATE = `CMD_STATE;
            CMD_BUS = SI_Reg[7:0];
            //$display( $time,"SI_Reg[7:0]= %h ", SI_Reg[7:0] );
            if ( During_RST_REC )
                $display ($time," During reset recovery time, there is command. \n");
        end

        if ( CS_INT == 1'b0 && ~HPM_RD && ( EN_Boot && !FBE ) ) begin
            STATE = `FAST_BOOT_STATE;
            if ( During_RST_REC )
                $display ($time," During reset recovery time, there is command. \n");
        end

        if ( (EN4XIO_Read_Mode && (Bit == 1 || (ENQUAD && Bit==7))) && CS_INT == 1'b0
             && HPM_RD && (SI_Reg[7:0]== RSTEN || SI_Reg[7:0]== RST)) begin
            CMD_BUS = SI_Reg[7:0];
            //$display( $time,"SI_Reg[7:0]= %h ", SI_Reg[7:0] );
        end

        if ( CS == 1'b1 && RST_CMD_EN &&
             ( (Bit+1)%8 == 0 || (EN4XIO_Read_Mode && !ENQUAD && (Bit+1)%2 == 0) ) ) begin
            RST_CMD_EN <= #1 1'b0;
        end
        
        case ( STATE )
            `STANDBY_STATE: 
                begin
                end

            `FAST_BOOT_STATE:
                begin
                    Read_SHSL = 1'b1;
                    FAST_BOOT_Mode = 1'b1;
                end

            `CMD_STATE: 
                begin
                    case ( CMD_BUS ) 
                    WREN: 
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin 
                                    // $display( $time, " Enter Write Enable Function ..." );
                                    write_enable;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE; 
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE; 
                        end
                     
                    WRDI:   
                        begin
                            if ( !DP_Mode && (!WIP || During_Susp_Wait) && Chip_EN && ~HPM_RD ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin 
                                    // $display( $time, " Enter Write Disable Function ..." );
                                    write_disable;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE; 
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE; 
                        end 

                  RDID:
                      begin
                          if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                              //$display( $time, " Enter Read ID Function ..." );
                               Read_SHSL = 1'b1;
                               RDID_Mode = 1'b1;
                           end
                          else if ( Bit == 7 )
                              STATE <= `BAD_CMD_STATE;
                        end

                    EN4B:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && !EPSUSP ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin
                                    // $display( $time, " Enter 4-byte mode ..." );
                                    CR[5] <= 1'b1;
                                    EN4B_Mode <= 1'b1;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    EX4B:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && !EPSUSP ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin
                                    // $display( $time, " Exit 4-byte mode ..." );
                                    CR[5] <= 1'b0;
                                    EN4B_Mode <= 1'b0;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                   QPIID:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && ENQUAD ) begin
                                //$display( $time, " Enter Read ID Function ..." );
                                Read_SHSL = 1'b1;
                                RDID_Mode = 1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                      
                    RDSR:
                        begin 
                            if ( !DP_Mode && Chip_EN && ~HPM_RD) begin 
                                //$display( $time, " Enter Read Status Function ..." );
                                Read_SHSL = 1'b1;
                                RDSR_Mode = 1'b1 ;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;        
                        end

                    RDCR:
                        begin
                            if ( !DP_Mode && Chip_EN && ~HPM_RD) begin
                                //$display( $time, " Enter Read Configuration Status Function ..." );
                                Read_SHSL = 1'b1;
                                RDCR_Mode = 1'b1 ;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

           
                    WRSR:
                        begin
                            if ( !DP_Mode && !WIP && WEL && Chip_EN && !Secur_Mode && ~HPM_RD && !EPSUSP ) begin
                                if ( CS_INT == 1'b1 && Bit == 15 || CS_INT == 1'b1 && Bit == 23 ) begin
                                    if ( Dis_WRSR ) begin 
                                        Status_Reg[1] = 1'b0; 
                                    end
                                    else if (CS_INT == 1'b1 && Bit == 15) begin 
                                        //$display( $time, " Enter Write Status Function ..." ); 
                                        ->WRSR_Event;
                                        WRSR_Mode = 1'b1;
                                    end 
                                    else if (CS_INT == 1'b1 && Bit == 23) begin                  
                                        //$display( $time, " Enter Write Status Function ..." ); 
                                        ->WRSR_Event;
                                        WRSR2_Mode = 1'b1;
                                    end
                 
                                end    
                                else if ( CS_INT == 1'b1 && (Bit < 15 || Bit > 15 && Bit < 23) )
                                    STATE <= `BAD_CMD_STATE;
                                else if ( (CS_INT == 1'b1 &&  Bit > 23) )

                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end 
                      
                    SBL:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD ) begin  // no WEL
                                if ( CS_INT == 1'b1 && Bit == 15 ) begin
                                    //$display( $time, " Enter Set Burst Length Function ..." );
                                    EN_Burst = !SI_Reg[4];
                                    if ( SI_Reg[7:5]==3'b000 && SI_Reg[3:2]==2'b00 ) begin
                                        if ( SI_Reg[1:0]==2'b00 )
                                            Burst_Length = 8;
                                        else if ( SI_Reg[1:0]==2'b01 )
                                            Burst_Length = 16;
                                        else if ( SI_Reg[1:0]==2'b10 )
                                            Burst_Length = 32;
                                        else if ( SI_Reg[1:0]==2'b11 )
                                            Burst_Length = 64;
                                    end
                                    else begin
                                        Burst_Length = 8;
                                    end
                                end
                                else if ( CS_INT == 1'b1 && Bit < 15 || Bit > 15 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    READ1X: 
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter Read Data Function ..." );
                                Read_SHSL = 1'b1;
                                if ( (Bit == 31 && !CR[5]) || (Bit == 39 && CR[5]) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                    load_address(Address);
                                end
                                Read_1XIO_Mode = 1'b1;
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                                
                        end

                    READ4B: 
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter Read Data Function ..." );
                                Read_SHSL = 1'b1;
                                if ( Bit == 39  ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    load_address(Address);
                                end
                                Read_1XIO_Mode = 1'b1;
                                ADD_4B_Mode = 1'b1;
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                                
                        end

                    FASTREAD1X:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter Fast Read Data Function ..." );
                                Read_SHSL = 1'b1;
                                if ( (Bit == 31 && !CR[5]) || (Bit == 39 && CR[5]) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                    load_address(Address);
                                end
                                FastRD_1XIO_Mode = 1'b1;
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                                
                        end

                    FASTREAD4B:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter Fast Read Data Function ..." );
                                Read_SHSL = 1'b1;
                                if ( Bit == 39 ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    load_address(Address);
                                end
                                FastRD_1XIO_Mode = 1'b1;
                                ADD_4B_Mode = 1'b1;
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                                
                        end

                    SE: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && !Secur_Mode &&  Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                if ( (Bit == 31 && !CR[5]) || (Bit == 39 && CR[5]) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                end
                                if ( CS_INT == 1'b1 && ((Bit == 31 && !CR[5]) || (Bit == 39 && CR[5])) ) begin
                                    //$display( $time, " Enter Sector Erase Function ..." );
                                    ->SE_4K_Event;
                                    SE_4K_Mode = 1'b1;
                                end
                                else if ( CS_INT == 1'b1 && ((Bit != 31 && !CR[5]) || (Bit != 39 && CR[5])) )
                                     STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    SE4B: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && !Secur_Mode &&  Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                ADD_4B_Mode = 1'b1;
                                if ( Bit == 39 ) begin
                                    Address = SI_Reg [A_MSB:0];
                                end
                                if ( CS_INT == 1'b1 && Bit == 39 ) begin
                                    //$display( $time, " Enter Sector Erase Function ..." );
                                    ->SE_4K_Event;
                                    SE_4K_Mode = 1'b1;
                                end
                                else if ( CS_INT == 1'b1 && Bit != 39 )
                                     STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    BE: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && !Secur_Mode &&  Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                if ( (Bit == 31 && !CR[5]) || (Bit == 39 && CR[5]) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                end
                                if ( CS_INT == 1'b1 && ((Bit == 31 && !CR[5]) || (Bit == 39 && CR[5])) ) begin
                                    //$display( $time, " Enter Block Erase Function ..." );
                                    ->BE_Event;
                                    BE_Mode = 1'b1;
                                    BE64K_Mode = 1'b1;
                                end
                                else if ( CS_INT == 1'b1 && ((Bit != 31 && !CR[5]) || (Bit != 39 && CR[5])) ) 
                                    STATE <= `BAD_CMD_STATE;
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    BE4B: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && !Secur_Mode &&  Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                ADD_4B_Mode = 1'b1;
                                if ( Bit == 39 ) begin
                                    Address = SI_Reg [A_MSB:0];
                                end
                                if ( CS_INT == 1'b1 && Bit == 39 ) begin
                                    //$display( $time, " Enter Block Erase Function ..." );
                                    ->BE_Event;
                                    BE_Mode = 1'b1;
                                    BE64K_Mode = 1'b1;
                                end 
                                else if ( CS_INT == 1'b1 && Bit != 39 )
                                    STATE <= `BAD_CMD_STATE;
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    BE32K:
                        begin
                            if ( !DP_Mode && !WIP && WEL && !Secur_Mode && Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                if ( (Bit == 31 && !CR[5]) || (Bit == 39 && CR[5]) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                end
                                if ( CS_INT == 1'b1 && ((Bit == 31 && !CR[5]) || (Bit == 39 && CR[5])) ) begin
                                    //$display( $time, " Enter Block 32K Erase Function ..." );
                                    ->BE32K_Event;
                                    BE_Mode = 1'b1;
                                    BE32K_Mode = 1'b1;
                                end
                                else if ( CS_INT == 1'b1 && ((Bit != 31 && !CR[5]) || (Bit != 39 && CR[5])) )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    BE32K4B:
                        begin
                            if ( !DP_Mode && !WIP && WEL && !Secur_Mode && Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                ADD_4B_Mode = 1'b1;
                                if ( Bit == 39 ) begin
                                    Address = SI_Reg [A_MSB:0];
                                end
                                if ( CS_INT == 1'b1 && Bit == 39  ) begin
                                    //$display( $time, " Enter Block 32K Erase Function ..." );
                                    ->BE32K_Event;
                                    BE_Mode = 1'b1;
                                    BE32K_Mode = 1'b1;
                                end
                                else if ( CS_INT == 1'b1 && Bit != 39 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    SUSP:
                        begin
                            if ( !DP_Mode && !Secur_Mode &&  Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin
                                    //$display( $time, " Enter Suspend Function ..." );
                                    ->Susp_Event;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    RESU:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && EPSUSP ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin
                                    //$display( $time, " Enter Resume Function ..." );
                                    Secur_Mode = 1'b0;
                                    ->Resume_Event;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end
                      
                    CE1, CE2:
                        begin
                            if ( !DP_Mode && !WIP && WEL && !Secur_Mode && Chip_EN && ~HPM_RD && !EPSUSP) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin
                                    //$display( $time, " Enter Chip Erase Function ..." );
                                    ->CE_Event;
                                    CE_Mode = 1'b1 ;
                                end 
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 ) 
                                STATE <= `BAD_CMD_STATE;
                        end
                      
                    PP: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && Chip_EN && ~HPM_RD && !PSB) begin
                                if ( (Bit == 31 && !CR[5]) || (Bit == 39 && CR[5]) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                    load_address(Address);
                                end

                                if ( (Bit == 31 && !CR[5]) || (Bit == 39 && CR[5]) ) begin
                                    //$display( $time, " Enter Page Program Function ..." );
                                    if ( CS_INT == 1'b0 ) begin
                                        ->PP_Event;
                                        PP_1XIO_Mode = 1'b1;
                                    end  
                                end
                                else if ( CS_INT == 1 &&( ( ((Bit < 39) || ((Bit + 1) % 8 !== 0))) ) && !CR[5] ) begin
                                    STATE <= `BAD_CMD_STATE;
                                end
                                else if ( CS_INT == 1 &&( ( ((Bit < 47) || ((Bit + 1) % 8 !== 0))) ) && CR[5] ) begin
                                    STATE <= `BAD_CMD_STATE;
                                end
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    PP4B: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && Chip_EN && ~HPM_RD && !PSB) begin
                                ADD_4B_Mode = 1'b1;
                                if ( Bit == 39 ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    load_address(Address);
                                end

                                if ( Bit == 39 ) begin
                                    //$display( $time, " Enter Page Program Function ..." );
                                    if ( CS_INT == 1'b0 ) begin
                                        ->PP_Event;
                                        PP_1XIO_Mode = 1'b1;
                                    end  
                                end
                                else if ( CS_INT == 1 &&( ( ((Bit < 47) || ((Bit + 1) % 8 !== 0))) ) ) begin
                                    STATE <= `BAD_CMD_STATE;
                                end
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    SFDP_READ:
                        begin
                            if ( !DP_Mode && !Secur_Mode && !WIP && Chip_EN && ~HPM_RD && !CR[5] ) begin
                                //$display( $time, " Enter SFDP read mode ..." );
                                if ( Bit == 31 ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    load_address(Address);
                                end
                                if ( Bit == 7 ) begin
                                    SFDP_Mode = 1;
                                    if (ENQUAD) begin
                                        Read_4XIO_Mode = 1'b1;
                                    end
                                    else begin
                                        FastRD_1XIO_Mode = 1'b1;
                                    end
                                    Read_SHSL = 1'b1;
                                end
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    RDFBR:
                        begin 
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin 
                                //$display( $time, " Enter Read Fast Boot Register Function ..." );
                                Read_SHSL = 1'b1;
                                RDFBR_Mode = 1'b1 ;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;        
                        end

                    WRFBR:
                        begin
                            if ( !DP_Mode && !WIP && WEL && Chip_EN && !Secur_Mode && ~HPM_RD && !EPSUSP && !ENQUAD ) begin
                                if ( CS_INT == 1'b0 && Bit == 7 ) begin
                                    //$display( $time, " Enter Write Fast Boot Register Function ..." ); 
                                    ->WRFBR_Event;
                                    WRFBR_Mode = 1'b1;
                                end    
                                else if ( CS_INT == 1'b1 && (Bit < 39 || Bit > 39) )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    ESFBR:
                        begin
                            if ( !DP_Mode && !WIP && WEL && Chip_EN && !Secur_Mode && ~HPM_RD && !EPSUSP && !ENQUAD ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin
                                    //$display( $time, " Enter Erase Fast Boot Register Function ..." );
                                    ->ESFBR_Event;
                                    ESFBR_Mode = 1'b1;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                           else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    DP:
                        begin
                            if ( !WIP && Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 && DP_Mode == 1'b0 ) begin
                                    //$display( $time, " Enter Deep Power Down Function ..." );
                                    tDP_Chk = 1'b1;
                                    DP_Mode = 1'b1;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    RDP, RES:
                        begin
                            if ( (!WIP || During_Susp_Wait) && Chip_EN && ~HPM_RD ) begin
                                // $display( $time, " Enter Release from Deep Power Down Function ..." );
                                if ( !CR[5] ) begin
                                    RES_Mode = 1'b1;
                                end
                                Read_SHSL = 1'b1;
                                if ( CS_INT == 1'b1 && SCLK == 1'b0 && tRES1_Chk &&
                                   ((Bit >= 38 && !ENQUAD) || (Bit >=38 && ENQUAD)) ) begin
                                    tRES1_Chk = 1'b0;
                                    tRES2_Chk = 1'b1;
                                    DP_Mode = 1'b0;
                                end
                                else if ( CS_INT == 1'b1 && SCLK == 1'b1 && tRES1_Chk &&
                                        ((Bit >= 39 && !ENQUAD) || (Bit >=39 && ENQUAD)) ) begin
                                    tRES1_Chk = 1'b0;
                                    tRES2_Chk = 1'b1;
                                    DP_Mode = 1'b0;
                                end
                                else if ( CS_INT == 1'b1 && Bit > 0 && DP_Mode ) begin
                                    tRES1_Chk = 1'b1;
                                    DP_Mode = 1'b0;
                                end
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    REMS:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD && !CR[5] ) begin
                                if ( Bit == 31 ) begin
                                    Address = SI_Reg[A_MSB:0] ;
                                end
                                //$display( $time, " Enter Read Electronic Manufacturer & ID Function ..." );
                                Read_SHSL = 1'b1;
                                REMS_Mode = 1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                            
                        end
                    READ2X: 
                        begin 
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter READX2 Function ..." );
                                Read_SHSL = 1'b1;
                                if ( (Bit == 19 && !CR[5]) || (Bit == 23 && CR[5]) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                    load_address(Address);
                                end
                                Read_2XIO_Mode = 1'b1;
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                                
                        end
                    READ2X4B: 
                        begin 
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter READX2 Function ..." );
                                Read_SHSL = 1'b1;
                                if ( Bit == 23 ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    load_address(Address);
                                end
                                Read_2XIO_Mode = 1'b1;
                                ADD_4B_Mode = 1'b1;
                            end 
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                                
                        end

                    ENSO: 
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin  
                                    //$display( $time, " Enter ENSO  Function ..." );
                                    enter_secured_otp;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end
                      
                    EXSO: 
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin  
                                    //$display( $time, " Enter EXSO  Function ..." );
                                    exit_secured_otp;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end
                      
                    RDSCUR: 
                        begin
                            if ( !DP_Mode && Chip_EN && ~HPM_RD) begin 
                                // $display( $time, " Enter Read Secur_Register Function ..." );
                                Read_SHSL = 1'b1;
                                RDSCUR_Mode = 1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                                
                        end
                      
                      
                    WRSCUR: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && !Secur_Mode && Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin  
                                    //$display( $time, " Enter WRSCUR Secur_Register Function ..." );
                                    ->WRSCUR_Event;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    RDEAR: 
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD) begin 
                                // $display( $time, " Enter Read Extended_Address_Register Function ..." );
                                Read_SHSL = 1'b1;
                                RDEAR_Mode = 1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                                
                        end

                    WREAR: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && !Secur_Mode && Chip_EN && ~HPM_RD && !EPSUSP ) begin
                                if ( CS_INT == 1'b1 && Bit == 15 ) begin  
                                    //$display( $time, " Enter WREAR Extended_Address_Register Function ..." );
                                    ->WREAR_Event;
                                end
                                else if ( CS_INT == 1'b1 && (Bit > 15 || Bit < 15) )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end
                      
                    READ4X:
                        begin
                            if ( !DP_Mode && !WIP && (Status_Reg[6]|ENQUAD) && Chip_EN && ~HPM_RD ) begin
                                //$display( $time, " Enter READX4 Function ..." );
                                Read_SHSL = 1'b1;
                                if ( (Bit == 13 && !CR[5] && !ENQUAD) || (Bit == 31 && !CR[5] && ENQUAD) || (Bit == 15 && CR[5] && !ENQUAD) || (Bit == 39 && CR[5] && ENQUAD) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                    load_address(Address);
                                end
                                Read_4XIO_Mode = 1'b1;
                                READ4X_Mode    = 1'b1;
                                READ4X_BOT_Mode    = 1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                            

                        end
                    READ4X_TOP:
                        begin
                            if ( !DP_Mode && !WIP && (Status_Reg[6]|ENQUAD) && Chip_EN && ~HPM_RD && !CR[5] ) begin
                                //$display( $time, " Enter READX4 Function ..." );
                                Read_SHSL = 1'b1;
                                if ( (Bit == 13 && !ENQUAD) || (Bit == 31 && ENQUAD) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    Address [24] = 1'b1;
                                    load_address(Address);
                                end
                                Read_4XIO_Mode = 1'b1;
                                READ4X_Mode    = 1'b1;
                                READ4X_TOP_Mode    = 1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                            

                        end

                    READ4X4B:
                        begin
                            if ( !DP_Mode && !WIP && (Status_Reg[6]|ENQUAD) && Chip_EN && ~HPM_RD ) begin
                                //$display( $time, " Enter READX4 Function ..." );
                                Read_SHSL = 1'b1;
                                if ( (Bit == 15 && !ENQUAD) || (Bit == 39 && ENQUAD) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    load_address(Address);
                                end
                                Read_4XIO_Mode = 1'b1;
                                READ4X4B_Mode    = 1'b1;
                                ADD_4B_Mode = 1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                            

                        end
                    DREAD:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter Fast Read dual output Function ..." );
                                Read_SHSL = 1'b1;
                                if ( (Bit == 31 && !CR[5]) || (Bit == 39 && CR[5]) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                    load_address(Address);
                                end
                                FastRD_2XIO_Mode =1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                            
                        end
                    DREAD4B:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter Fast Read dual output Function ..." );
                                Read_SHSL = 1'b1;
                                if ( Bit == 39 ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    load_address(Address);
                                end
                                FastRD_2XIO_Mode =1'b1;
                                ADD_4B_Mode = 1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;                            
                        end

                    QREAD:
                        begin
                            if ( !DP_Mode && !WIP && Status_Reg[6] && Chip_EN  && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter Fast Read quad output Function ..." );
                                Read_SHSL = 1'b1;
                                if ( (Bit == 31 && !CR[5]) || (Bit == 39 && CR[5]) ) begin 
                                   Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                   load_address(Address);
                                end
                                FastRD_4XIO_Mode =1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    QREAD4B:
                        begin
                            if ( !DP_Mode && !WIP && Status_Reg[6] && Chip_EN  && ~HPM_RD && !ENQUAD ) begin
                                //$display( $time, " Enter Fast Read quad output Function ..." );
                                Read_SHSL = 1'b1;
                                if ( Bit == 39 ) begin 
                                   Address = SI_Reg [A_MSB:0];
                                   load_address(Address);
                                end
                                FastRD_4XIO_Mode =1'b1;
                                ADD_4B_Mode = 1'b1;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end
                      
                    FIOPGM0: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && Status_Reg[6] && Chip_EN && ~HPM_RD && !ENQUAD && !PSB) begin
                                if ( (Bit == 13 && !CR[5]) || (Bit == 15 && CR[5]) ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    if ( !CR[5] ) begin
                                            Address [24] = EA_Reg[0];
                                    end
                                    load_address(Address);
                                end
                                PP_4XIO_Load= 1'b1;
                                SO_IN_EN    = 1'b1;
                                SI_IN_EN    = 1'b1;
                                WP_IN_EN    = 1'b1;
                                SIO3_IN_EN  = 1'b1;
                                if ( CS_INT == 0 && ((Bit == 13 && !CR[5]) || (Bit == 15 && CR[5])) ) begin
                                    //$display( $time, " Enter 4io Page Program Function ..." );
                                    ->PP_Event;
                                    PP_4XIO_Mode= 1'b1;
                                end
                                else if ( CS_INT == 1 && (Bit < 15 || (Bit + 1)%2 !== 0 ) && !CR[5])begin
                                    STATE <= `BAD_CMD_STATE;
                                end
                                else if ( CS_INT == 1 && (Bit < 17 || (Bit + 1)%2 !== 0 ) && CR[5])begin
                                    STATE <= `BAD_CMD_STATE;
                                end    
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    FIOPGM04B: 
                        begin
                            if ( !DP_Mode && !WIP && WEL && Status_Reg[6] && Chip_EN && ~HPM_RD && !ENQUAD && !PSB) begin
                                ADD_4B_Mode = 1'b1;
                                if ( Bit == 15 ) begin
                                    Address = SI_Reg [A_MSB:0];
                                    load_address(Address);
                                end
                                PP_4XIO_Load= 1'b1;
                                SO_IN_EN    = 1'b1;
                                SI_IN_EN    = 1'b1;
                                WP_IN_EN    = 1'b1;
                                SIO3_IN_EN  = 1'b1;
                                if ( CS_INT == 0 && Bit == 15 ) begin
                                    //$display( $time, " Enter 4io Page Program Function ..." );
                                    ->PP_Event;
                                    PP_4XIO_Mode= 1'b1;
                                end
                                else if ( CS_INT == 1 && (Bit < 17 || (Bit + 1)%2 !== 0 ) )begin
                                    STATE <= `BAD_CMD_STATE;
                                end    
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    EQIO:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && !ENQUAD ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin
                                    //$display( $time, " Enable Quad I/O Function ..." );
                                    ENQUAD = 1'b1;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    RSTQIO:
                        begin
                            if ( !DP_Mode && !WIP && Chip_EN && ~HPM_RD && ENQUAD ) begin
                                if ( CS_INT == 1'b1 && Bit == 7 ) begin
                                    //$display( $time, " Exiting QPI mode ..." );
                                    ENQUAD = 1'b0;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    RSTEN:
                        begin
                            if ( Chip_EN ) begin
                                if ( CS_INT == 1'b1 && (Bit == 7 || (EN4XIO_Read_Mode && Bit == 1)) ) begin
                                    //$display( $time, " Reset enable ..." );
                                    ->RST_EN_Event;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    RST:
                        begin
                            if ( Chip_EN && RST_CMD_EN ) begin
                                if ( CS_INT == 1'b1 && (Bit == 7 || (EN4XIO_Read_Mode && Bit == 1)) ) begin
                                    //$display( $time, " Reset memory ..." );
                                    ->RST_Event;
                                end
                                else if ( Bit > 7 )
                                    STATE <= `BAD_CMD_STATE;
                            end
                            else if ( Bit == 7 )
                                STATE <= `BAD_CMD_STATE;
                        end

                    NOP:
                        begin
                        end

                    default: 
                        begin
                            STATE <= `BAD_CMD_STATE;
                        end
                    endcase
                end
                 
            `BAD_CMD_STATE: 
                begin
                end
            
            default: 
                begin
                STATE =  `STANDBY_STATE;
                end
        endcase

        if ( CS_INT == 1'b1 ) begin

        end
    end

    always @ (posedge CS_INT) begin
            SIO0_Reg <= #tSHQZ 1'bx;
            SIO1_Reg <= #tSHQZ 1'bx;
            SIO2_Reg <= #tSHQZ 1'bx;
            SIO3_Reg <= #tSHQZ 1'bx;
            SIO0_Out_Reg <= #tSHQZ 1'bx;
            SIO1_Out_Reg <= #tSHQZ 1'bx;
            SIO2_Out_Reg <= #tSHQZ 1'bx;
            SIO3_Out_Reg <= #tSHQZ 1'bx;
           
            SO_OUT_EN    <= #tSHQZ 1'b0;
            SI_OUT_EN    <= #tSHQZ 1'b0;
            WP_OUT_EN    <= #tSHQZ 1'b0;
            SIO3_OUT_EN  <= #tSHQZ 1'b0;

            #1;
            Bit         = 1'b0;
            Bit_Tmp     = 1'b0;
           
            SO_IN_EN    = 1'b0;
            SI_IN_EN    = 1'b0;
            WP_IN_EN    = 1'b0;
            SIO3_IN_EN  = 1'b0;

            RDID_Mode   = 1'b0;
            RDSR_Mode   = 1'b0;
            RDCR_Mode   = 1'b0;
            RDSCUR_Mode = 1'b0;
            RDFBR_Mode   = 1'b0;
            RDEAR_Mode = 1'b0;
            Read_Mode   = 1'b0;
            RES_Mode    = 1'b0;
            REMS_Mode   = 1'b0;
            SFDP_Mode    = 1'b0;
            Read_1XIO_Mode  = 1'b0;
            Read_2XIO_Mode  = 1'b0;
            Read_4XIO_Mode  = 1'b0;
            Read_1XIO_Chk   = 1'b0;
            Read_2XIO_Chk   = 1'b0;
            Read_4XIO_Chk   = 1'b0;
            FastRD_1XIO_Mode= 1'b0;
            FastRD_1XIO_Chk = 1'b0;
            FastRD_2XIO_Mode= 1'b0;
            FastRD_2XIO_Chk = 1'b0;
            FastRD_4XIO_Mode= 1'b0;
            FastRD_4XIO_Chk = 1'b0;
            PP_4XIO_Load    = 1'b0;
            PP_4XIO_Chk     = 1'b0;
            STATE <=  `STANDBY_STATE;

            if( Chip_EN ) begin
                EN_Boot     = 1'b0;
            end
            FAST_BOOT_Mode  = 1'b0;
            FAST_BOOT_Chk   = 1'b0;

            ADD_4B_Mode = 1'b0;

            disable read_id;
            disable read_status;
            disable read_Secur_Register;
            disable read_EA_Register;
            disable read_FB_register;
            disable read_1xio;
            disable read_2xio;
            disable read_4xio;
            disable fastread_1xio;
            disable fastread_2xio;
            disable fastread_4xio;
            disable read_electronic_id;
            disable read_electronic_manufacturer_device_id;
            disable read_function;
            disable dummy_cycle;
            disable read_cr;
            disable fast_boot_read;
        end

    always @ (posedge CS_INT) begin 

        if ( Set_4XIO_Enhance_Mode) begin
            EN4XIO_Read_Mode = 1'b1;
        end
        else begin
            EN4XIO_Read_Mode = 1'b0;
            READ4X4B_Mode    = 1'b0;
            READ4X_Mode    = 1'b0;
            READ4X_TOP_Mode    = 1'b0;
            READ4X_BOT_Mode    = 1'b0;
        end
    end 

    /*----------------------------------------------------------------------*/
    /*  ALL function trig action                                            */
    /*----------------------------------------------------------------------*/
    always @ ( posedge Read_1XIO_Mode
            or posedge FastRD_1XIO_Mode
            or posedge REMS_Mode
            or posedge RES_Mode
            or posedge Read_2XIO_Mode
            or posedge Read_4XIO_Mode 
            or posedge PP_4XIO_Load
            or posedge FastRD_2XIO_Mode
            or posedge FastRD_4XIO_Mode
           ) begin:read_function 
        wait ( SCLK == 1'b0 );
        if ( Read_1XIO_Mode == 1'b1 ) begin
            Read_1XIO_Chk = 1'b1;
            read_1xio;
        end
        else if ( FastRD_1XIO_Mode == 1'b1 ) begin
            FastRD_1XIO_Chk = 1'b1;
            fastread_1xio;
        end
        else if ( FastRD_2XIO_Mode == 1'b1 ) begin
            FastRD_2XIO_Chk = 1'b1;
            fastread_2xio;
        end
        else if ( FastRD_4XIO_Mode == 1'b1 ) begin
            FastRD_4XIO_Chk = 1'b1;
            fastread_4xio;
        end
        else if ( REMS_Mode == 1'b1 ) begin
            read_electronic_manufacturer_device_id;
        end 
        else if ( RES_Mode == 1'b1 ) begin
            read_electronic_id;
        end
        else if ( Read_2XIO_Mode == 1'b1 ) begin
            Read_2XIO_Chk = 1'b1;
            read_2xio;
        end
        else if ( Read_4XIO_Mode == 1'b1 ) begin
            Read_4XIO_Chk = 1'b1;
            read_4xio;
        end   
        else if ( PP_4XIO_Load == 1'b1 ) begin
            PP_4XIO_Chk = 1'b1;
        end
    end

    always @ ( posedge FAST_BOOT_Mode ) begin
            FAST_BOOT_Chk = 1'b1;
            fast_boot_read;
    end

    always @ ( RST_EN_Event ) begin
        RST_CMD_EN = #2 1'b1;
    end
    
    always @ ( RST_Event ) begin
        During_RST_REC = 1;
        if ((WRSR_Mode||WRSR2_Mode) && tWRSR==tW) begin
            #(tREADY2_W);
        end
        else if ((WRSR_Mode||WRSR2_Mode) && tWRSR==tBP) begin
            #(tREADY2_W);
        end
        else if ( WRFBR_Mode || WRSCUR_Mode ||  PP_4XIO_Mode || PP_1XIO_Mode ) begin
            #(tREADY2_P);
        end
        else if ( SE_4K_Mode || ESFBR_Mode ) begin
            #(tREADY2_SE);
        end
        else if ( BE64K_Mode || BE32K_Mode ) begin
            #(tREADY2_BE);
        end
        else if ( CE_Mode ) begin
            #(tREADY2_CE);
        end
        else if ( DP_Mode == 1'b1 ) begin
            #(tRES2);
        end
        else if ( Read_SHSL == 1'b1 ) begin
            #(tREADY2_R);
        end
        else begin
            #(tREADY2_D);
        end
        disable write_status;
        disable write_FB_register;
        disable erase_FB_register;
        disable block_erase_32k;
        disable block_erase;
        disable sector_erase_4k;
        disable chip_erase;
        disable page_program; // can deleted
        disable update_array;
        disable read_Secur_Register;
        disable read_EA_Register;
        disable write_secur_register;
        disable write_ea_register;
        disable read_id;
        disable read_status;
        disable read_FB_register;
        disable suspend_write;
        disable resume_write;
        disable er_timer;
        disable pg_timer;
        disable stimeout_cnt;
        disable rtimeout_cnt;

        disable read_1xio;
        disable read_2xio;
        disable read_4xio;
        disable fastread_1xio;
        disable fastread_2xio;
        disable fastread_4xio;
        disable read_electronic_id;
        disable read_electronic_manufacturer_device_id;
        disable read_function;
        disable dummy_cycle;
        disable read_cr;

        disable fast_boot_read;

        reset_sm;
        Status_Reg[1:0] = 2'b0;
        Secur_Reg[6:2]  = 5'b0;
        CR[2:0]         = 3'b111;
        CR[5]           = 1'b0;
        CR[7:6]         = 2'b00;
        EA_Reg          = 8'b0000_0000;

    end
    
// *==============================================================================================
// * Hardware Reset Function description
// * ============================================================================================
    always @ ( negedge RESETB_INT ) begin
        if (RESETB_INT == 1'b0) begin
            disable hd_reset;
            #0;
            -> HDRST_Event;
        end
    end
    always @ ( HDRST_Event ) begin: hd_reset
      if (RESETB_INT == 1'b0) begin
        During_RST_REC = 1;
        if ((WRSR_Mode||WRSR2_Mode) && tWRSR==tW) begin
            #(tREADY2_W);
        end
        else if ((WRSR_Mode||WRSR2_Mode) && tWRSR==tBP) begin
            #(tREADY2_W);
        end
        else if ( WRFBR_Mode || WRSCUR_Mode ||  PP_4XIO_Mode || PP_1XIO_Mode ) begin
            #(tREADY2_P);
        end
        else if ( SE_4K_Mode || ESFBR_Mode ) begin
            #(tREADY2_SE);
        end
        else if ( BE64K_Mode || BE32K_Mode ) begin
            #(tREADY2_BE);
        end
        else if ( CE_Mode ) begin
            #(tREADY2_CE);
        end
        else if ( DP_Mode == 1'b1 ) begin
            #(tRES2+tRLRH);
        end
        else if ( Read_SHSL == 1'b1 ) begin
            #(tREADY2_R);
        end
        else begin
            #(tREADY2_D);
        end
        disable write_status;
        disable write_FB_register;
        disable erase_FB_register;
        disable block_erase_32k;
        disable block_erase;
        disable sector_erase_4k;
        disable chip_erase;
        disable page_program; // can deleted
        disable update_array;
        disable read_Secur_Register;
        disable read_EA_Register;
        disable write_secur_register;
        disable write_ea_register;
        disable read_id;
        disable read_status;
        disable read_FB_register;
        disable suspend_write;
        disable resume_write;
        disable er_timer;
        disable pg_timer;
        disable stimeout_cnt;
        disable rtimeout_cnt;

        disable read_1xio;
        disable read_2xio;
        disable read_4xio;
        disable fastread_1xio;
        disable fastread_2xio;
        disable fastread_4xio;
        disable read_electronic_id;
        disable read_electronic_manufacturer_device_id;
        disable read_function;
        disable dummy_cycle;
        disable read_cr;

        disable fast_boot_read;

        reset_sm;
        Status_Reg[1:0] = 2'b0;
        Secur_Reg[6:2]  = 5'b0;
        CR[2:0]         = 3'b111;
        CR[5]           = 1'b0;
        CR[7:6]         = 2'b00;
        EA_Reg          = 8'b0000_0000;
      end
    end


    always @ ( posedge Susp_Trig ) begin:stimeout_cnt
        Susp_Trig <= #1 1'b0;
    end

    always @ ( posedge Resume_Trig ) begin:rtimeout_cnt
        Resume_Trig <= #1 1'b0;
    end


    always @ ( posedge READ4X4B_Mode ) begin
        READ4X_Mode = 1'b0;
    end

    always @ ( posedge READ4X_BOT_Mode ) begin
        READ4X_TOP_Mode = 1'b0;
    end

    always @ ( WRSR_Event ) begin
        write_status;
    end

    always @ ( WRFBR_Event ) begin
        write_FB_register;
    end

    always @ ( ESFBR_Event ) begin
        erase_FB_register;
    end

    always @ ( BE_Event ) begin
        block_erase;
    end

    always @ ( CE_Event ) begin
        chip_erase;
    end
    
    always @ ( PP_Event ) begin:page_program_mode
        page_program( Address );
    end
   
    always @ ( SE_4K_Event ) begin
        sector_erase_4k;
    end

    always @ ( posedge RDID_Mode ) begin
        read_id;
    end

    always @ ( posedge RDSR_Mode ) begin
        read_status;
    end

    always @ ( posedge RDCR_Mode ) begin
        read_cr;
    end

    always @ ( posedge RDSCUR_Mode ) begin
        read_Secur_Register;
    end

    always @ ( posedge RDFBR_Mode ) begin
        read_FB_register;
    end

    always @ ( WRSCUR_Event ) begin
        write_secur_register;
    end

    always @ ( Susp_Event ) begin
        suspend_write;
    end

    always @ ( Resume_Event ) begin
        resume_write;
    end

    always @ ( posedge RDEAR_Mode ) begin
        read_EA_Register;
    end

    always @ ( WREAR_Event ) begin
        write_ea_register;
    end

    always @ ( BE32K_Event ) begin
        block_erase_32k;
    end



// *========================================================================================== 
// * Module Task Declaration
// *========================================================================================== 
    /*----------------------------------------------------------------------*/
    /*  Description: define a wait dummy cycle task                         */
    /*  INPUT                                                               */
    /*      Cnum: cycle number                                              */
    /*----------------------------------------------------------------------*/
    task dummy_cycle;
        input [31:0] Cnum;
        begin
            repeat( Cnum ) begin
                @ ( posedge SCLK );
            end
        end
    endtask // dummy_cycle

    /*----------------------------------------------------------------------*/
    /*  Description: define a write enable task                             */
    /*----------------------------------------------------------------------*/
    task write_enable;
        begin
            //$display( $time, " Old Status Register = %b", Status_Reg );
            Status_Reg[1] = 1'b1; 
            // $display( $time, " New Status Register = %b", Status_Reg );
        end
    endtask // write_enable
    
    /*----------------------------------------------------------------------*/
    /*  Description: define a write disable task (WRDI)                     */
    /*----------------------------------------------------------------------*/
    task write_disable;
        begin
            //$display( $time, " Old Status Register = %b", Status_Reg );
            Status_Reg[1]  = 1'b0;
            //$display( $time, " New Status Register = %b", Status_Reg );
        end
    endtask // write_disable
    
    /*----------------------------------------------------------------------*/
    /*  Description: define a read id task (RDID)                           */
    /*----------------------------------------------------------------------*/
    task read_id;
        reg  [23:0] Dummy_ID;
        integer Dummy_Count;
        begin
                Dummy_ID = {ID_MXIC, Memory_Type, Memory_Density};
                if (ENQUAD)
                        Dummy_Count = 6;
                else
                        Dummy_Count = 24;
                forever begin
                        @ ( negedge SCLK or posedge CS_INT );
                        if ( CS_INT == 1'b1 ) begin
                                disable read_id;
                        end
                        else begin
                                if (ENQUAD) begin
                                        SI_OUT_EN   = 1'b1;
                                        WP_OUT_EN   = 1'b1;
                                        SIO3_OUT_EN = 1'b1;
                                end
                                SO_OUT_EN = 1'b1;
                                SO_IN_EN  = 1'b0;
                                SI_IN_EN  = 1'b0;
                                WP_IN_EN  = 1'b0;
                                SIO3_IN_EN= 1'b0;
                                if ( Dummy_Count ) begin
                                        Dummy_Count = Dummy_Count - 1;
                                        if (ENQUAD) begin
                                                if ( Dummy_Count == 5 )
                                                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_ID[23:20];
                                                else if ( Dummy_Count == 4 )
                                                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_ID[19:16];
                                                else if ( Dummy_Count == 3 )
                                                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_ID[15:12];
                                                else if ( Dummy_Count == 2 )
                                                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_ID[11:8];
                                                else if ( Dummy_Count == 1 )
                                                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_ID[7:4];
                                                else if ( Dummy_Count == 0 )
                                                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_ID[3:0];
                                        end
                                        else begin
                                                SIO1_Reg <= Dummy_ID[Dummy_Count];
                                        end
                                end
                                else begin
                                        if (ENQUAD) begin
                                                Dummy_Count = 5;
                                                {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_ID[23:20];
                                        end
                                        else begin
                                                Dummy_Count = 23;
                                                SIO1_Reg <= Dummy_ID[Dummy_Count];
                                        end
                                end
                        end
                end  // end forever
        end
    endtask // read_id
    
    /*----------------------------------------------------------------------*/
    /*  Description: define a read status task (RDSR)                       */
    /*----------------------------------------------------------------------*/
    task read_status;
        reg [7:0] Status_Reg_Int;
        integer Dummy_Count;
        begin
            Status_Reg_Int = Status_Reg;
            if (ENQUAD) begin
                Dummy_Count = 2;
            end
            else begin
                Dummy_Count = 8;
            end
            forever begin
                @ ( negedge SCLK or posedge CS_INT );
                if ( CS_INT == 1'b1 ) begin
                    disable read_status;
                end
                else begin
                    if (ENQUAD) begin
                        SI_OUT_EN    = 1'b1;
                        WP_OUT_EN    = 1'b1;
                        SIO3_OUT_EN  = 1'b1;
                    end
                    SO_OUT_EN = 1'b1;
                    SO_IN_EN  = 1'b0;
                    SI_IN_EN  = 1'b0;
                    WP_IN_EN  = 1'b0;
                    SIO3_IN_EN= 1'b0;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        if (ENQUAD) begin
                            {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_Count ?
                                                          Status_Reg_Int[7:4] : Status_Reg_Int[3:0];
                        end
                        else begin
                            SIO1_Reg    <= Status_Reg_Int[Dummy_Count];
                        end
                    end
                    else begin
                        if (ENQUAD) begin
                            Dummy_Count = 1;
                            Status_Reg_Int = Status_Reg;
                            {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Status_Reg_Int[7:4];
                        end
                        else begin
                            Dummy_Count = 7;
                            Status_Reg_Int = Status_Reg;
                            SIO1_Reg    <= Status_Reg_Int[Dummy_Count];
                        end
                    end          
                end
            end  // end forever
        end
    endtask // read_status

    /*----------------------------------------------------------------------*/
    /*  Description: define a read configuration register task (RDCR)                       */
    /*----------------------------------------------------------------------*/
    task read_cr;
        integer Dummy_Count;
        begin
            if (ENQUAD) begin
                Dummy_Count = 2;
            end
            else begin
                Dummy_Count = 8;
            end
            forever begin
                @ ( negedge SCLK or posedge CS_INT );
                if ( CS_INT == 1'b1 ) begin
                    disable read_cr;
                end
                else begin
                    if (ENQUAD) begin
                        SI_OUT_EN    = 1'b1;
                        WP_OUT_EN    = 1'b1;
                        SIO3_OUT_EN  = 1'b1;
                    end
                    SO_OUT_EN = 1'b1;
                    SO_IN_EN  = 1'b0;
                    SI_IN_EN  = 1'b0;
                    WP_IN_EN  = 1'b0;
                    SIO3_IN_EN= 1'b0;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        if (ENQUAD) begin
                            {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_Count ?
                                                          CR[7:4] : CR[3:0];
                        end
                        else begin
                            SIO1_Reg    <= CR[Dummy_Count];
                        end
                    end
                    else begin
                        if (ENQUAD) begin
                            Dummy_Count = 1;
                            {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= CR[7:4];
                        end
                        else begin
                            Dummy_Count = 7;
                            SIO1_Reg    <= CR[Dummy_Count];
                        end
                    end          
                end
            end  // end forever
        end
    endtask // read_cr

    /*----------------------------------------------------------------------*/
    /*  Description: define a write status task                             */
    /*----------------------------------------------------------------------*/
    task write_status;
    reg [7:0] Status_Reg_Up;
    reg [7:0] CR_Up;
        begin
            //$display( $time, " Old Status Register = %b", Status_Reg );
          if (WRSR_Mode == 1'b0 && WRSR2_Mode == 1'b1) begin
            Status_Reg_Up = SI_Reg[15:8] ;
            CR_Up = SI_Reg [7:0];
          end
          else if (WRSR_Mode == 1'b1 && WRSR2_Mode == 1'b0) begin
            Status_Reg_Up = SI_Reg[7:0] ;
          end

          if (WRSR_Mode == 1'b1 && WRSR2_Mode == 1'b0) begin       //for one byte WRSR write
                tWRSR = tW;
                Secur_Reg[5] = 1'b0;
                if ( (Status_Reg[7] == 1'b1 && Status_Reg_Up[7] == 1'b0 ) ||
                     (Status_Reg[6] == 1'b1 && Status_Reg_Up[6] == 1'b0 ) ||
                     (Status_Reg[5] == 1'b1 && Status_Reg_Up[5] == 1'b0 ) ||
                     (Status_Reg[4] == 1'b1 && Status_Reg_Up[4] == 1'b0 ) ||
                     (Status_Reg[3] == 1'b1 && Status_Reg_Up[3] == 1'b0 ) ||
                     (Status_Reg[2] == 1'b1 && Status_Reg_Up[2] == 1'b0 ))
                begin
                    Secur_Reg[6] = 1'b0;
                end
                //SRWD:Status Register Write Protect
                Status_Reg[0]   = 1'b1;
                #tWRSR;
                Status_Reg[7]   =  Status_Reg_Up[7];
                Status_Reg[6:2] =  Status_Reg_Up[6:2];
                //WIP : write in process Bit
                Status_Reg[0]   = 1'b0;
                //WEL:Write Enable Latch
                Status_Reg[1]   = 1'b0;
                WRSR_Mode       = 1'b0;
          end    

          else if (WRSR_Mode == 1'b0 && WRSR2_Mode == 1'b1) begin  //for two byte WRSR write
                tWRSR = tW;
                Secur_Reg[5] = 1'b0;
                if ( (Status_Reg[7] == 1'b1 && Status_Reg_Up[7] == 1'b0 ) ||
                     (Status_Reg[6] == 1'b1 && Status_Reg_Up[6] == 1'b0 ) ||
                     (Status_Reg[5] == 1'b1 && Status_Reg_Up[5] == 1'b0 ) ||
                     (Status_Reg[4] == 1'b1 && Status_Reg_Up[4] == 1'b0 ) ||
                     (Status_Reg[3] == 1'b1 && Status_Reg_Up[3] == 1'b0 ) ||
                     (Status_Reg[2] == 1'b1 && Status_Reg_Up[2] == 1'b0 ) ) begin
                    Secur_Reg[6] = 1'b0;
                end
                //SRWD:Status Register Write Protect
                Status_Reg[0]   = 1'b1;
                #tWRSR;
                if ( CR[3] == 1'b1 ) begin
                    CR[3] = 1'b1;
                end
                else begin
                    CR[3] = CR_Up[3];
                end
                CR[2:0]         =  CR_Up[2:0];
                if (`F133 == 1'b1) begin
                        CR[7:6] =  CR_Up[7:6];
                end
                else begin
                        CR[7:6] =  (CR_Up[7:6]==2'b11) ? CR[7:6] : CR_Up[7:6];
                end
                Status_Reg[7]   =  Status_Reg_Up[7];
                Status_Reg[6:2] =  Status_Reg_Up[6:2];
                //WIP : write in process Bit
                Status_Reg[0]   = 1'b0;
                //WEL:Write Enable Latch
                Status_Reg[1]   = 1'b0;
                WRSR2_Mode      = 1'b0;
          end
        end
    endtask // write_status
  
    /*----------------------------------------------------------------------*/
    /*  Description: define a fast boot read data task                      */
    /*----------------------------------------------------------------------*/
    task fast_boot_read;
        integer Dummy_Count, Tmp_Int;
        reg  [7:0]       OUT_Buf;
        begin

            Dummy_Count = Status_Reg[6] ? 2 : 8;

            if ( FB_Reg[2:1] == 2'b00 )
                    dummy_cycle(6);
            else if ( FB_Reg[2:1] == 2'b01 )
                    dummy_cycle(8);
            else if ( FB_Reg[2:1] == 2'b10 )
                    dummy_cycle(10);
            else if ( FB_Reg[2:1] == 2'b11 )
                    dummy_cycle(12);

            Address = { FB_Reg[31:4], 4'b0000 };
            read_array(Address, OUT_Buf);
            forever begin
                @ ( negedge SCLK or posedge CS_INT );
                if ( CS_INT == 1'b1 ) begin
                    disable fast_boot_read;
                end 
                else begin
                    if ( Status_Reg[6] == 1'b0 ) begin
                        Read_Mode = 1'b1;
                        SO_OUT_EN = 1'b1;
                        SI_IN_EN  = 1'b0;
                        if ( Dummy_Count ) begin
                                Dummy_Count = Dummy_Count - 1;
                                SIO1_Reg <= OUT_Buf[Dummy_Count];
                        end
                        else begin
                                Address = Address + 1;
                                read_array(Address, OUT_Buf);
                                Dummy_Count = 7;
                                SIO1_Reg <= OUT_Buf[Dummy_Count];
                        end
                    end
                    else if ( Status_Reg[6] == 1'b1 ) begin
                        SO_OUT_EN   = 1'b1;
                        SI_OUT_EN   = 1'b1;
                        WP_OUT_EN   = 1'b1;
                        SIO3_OUT_EN = 1'b1;
                        SO_IN_EN    = 1'b0;
                        SI_IN_EN    = 1'b0;
                        WP_IN_EN    = 1'b0;
                        SIO3_IN_EN  = 1'b0;
                        Read_Mode  = 1'b1;
                        if ( Dummy_Count ) begin
                                Dummy_Count = Dummy_Count - 1;
                                {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_Count ? OUT_Buf[7:4] : OUT_Buf[3:0];
                        end
                        else begin
                                Address = Address + 1;
                                read_array(Address, OUT_Buf);
                                Dummy_Count = 1;
                                {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= OUT_Buf[7:4];
                        end
                    end
                end    
            end  // end forever
        end   
    endtask // fast_boot_read

    /*----------------------------------------------------------------------*/
    /*  Description: define a read data task                                */
    /*               03 AD1 AD2 AD3 X                                       */
    /*----------------------------------------------------------------------*/
    task read_1xio;
        integer Dummy_Count, Tmp_Int;
        reg  [7:0]       OUT_Buf;
        begin
            Dummy_Count = 8;
            if ( !CR[5] && !ADD_4B_Mode )
                    dummy_cycle(24);
            else if ( CR[5] || ADD_4B_Mode )
                    dummy_cycle(32);
            #1; 
            read_array(Address, OUT_Buf);
            forever begin
                @ ( negedge SCLK or posedge CS_INT );
                if ( CS_INT == 1'b1 ) begin
                    disable read_1xio;
                end 
                else  begin 
                    Read_Mode   = 1'b1;
                    SO_OUT_EN   = 1'b1;
                    SI_IN_EN    = 1'b0;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        SIO1_Reg <= OUT_Buf[Dummy_Count];
                    end
                    else begin
                        Address = Address + 1;
                        load_address(Address);
                        read_array(Address, OUT_Buf);
                        Dummy_Count = 7;
                        SIO1_Reg <= OUT_Buf[Dummy_Count];
                    end
                end 
            end  // end forever
        end   
    endtask // read_1xio

    /*----------------------------------------------------------------------*/
    /*  Description: define a fast read data task                           */
    /*               0B AD1 AD2 AD3 X                                       */
    /*----------------------------------------------------------------------*/
    task fastread_1xio;
        integer Dummy_Count, Tmp_Int;
        reg  [7:0]       OUT_Buf;
        begin
            Dummy_Count = 8;
            if ( !CR[5] && !ADD_4B_Mode )
                    dummy_cycle(24);
            else if ( CR[5] || ADD_4B_Mode )
                    dummy_cycle(32);

            if ( SFDP_Mode == 1 )
                    dummy_cycle(8);
            else begin
                if ( CR[7:6] == 2'b00 )
                    dummy_cycle(8);
                else if ( CR[7:6] == 2'b01 )
                    dummy_cycle(6);
                else if ( CR[7:6] == 2'b10 )
                    dummy_cycle(8);
                else if ( CR[7:6] == 2'b11 )
                    dummy_cycle(10);
            end

            #1;
            read_array(Address, OUT_Buf);
            forever begin
                @ ( negedge SCLK or posedge CS_INT );
                if ( CS_INT == 1'b1 ) begin
                    disable fastread_1xio;
                end 
                else begin 
                    Read_Mode = 1'b1;
                    SO_OUT_EN = 1'b1;
                    SI_IN_EN  = 1'b0;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        SIO1_Reg <= OUT_Buf[Dummy_Count];
                    end
                    else begin
                        Address = Address + 1;
                        load_address(Address);
                        read_array(Address, OUT_Buf);
                        Dummy_Count = 7;
                        SIO1_Reg <= OUT_Buf[Dummy_Count];
                    end
                end    
            end  // end forever
        end   
    endtask // fastread_1xio

    /*----------------------------------------------------------------------*/
    /*  Description: Execute Write Fast Boot Register                       */
    /*----------------------------------------------------------------------*/
    task write_FB_register;
        reg [31:0] FB_Reg_Up;
        reg [31:0] FB_Reg_Old;
        integer Tmp_Int, i;
        begin
            FB_Reg_Up = 32'hffff_ffff;
            FB_Reg_Old = FB_Reg;
            Tmp_Int = 0;
            forever begin
                @ ( posedge SCLK or posedge CS_INT );
                if ( CS_INT == 1'b1 ) begin
                    if ( Tmp_Int != 32 ) begin
                        WRFBR_Mode = 0;
                        disable write_FB_register;
                    end
                    else begin
                        Secur_Reg[5] = 1'b0;
                        Status_Reg[0] = 1'b1;
                        #tWRFBR;
                        FB_Reg = FB_Reg_Up & FB_Reg_Old;
                        //WIP : write in process Bit
                        Status_Reg[0] = 1'b0;
                        //WEL:Write Enable Latch
                        Status_Reg[1] = 1'b0;
                        WRFBR_Mode = 1'b0;
                    end
                    disable write_FB_register;
                end
                else begin
                    Tmp_Int = Tmp_Int + 1;
                    if ( Tmp_Int <= 32 ) begin  
                        if ( Tmp_Int % 8 == 0) begin
                                #1;
                                if ( Tmp_Int == 8 ) begin
                                        FB_Reg_Up[7:0] = SI_Reg[7:0];
                                end
                                else if ( Tmp_Int == 16 ) begin
                                        FB_Reg_Up[15:8] = SI_Reg[7:0];
                                end
                                else if ( Tmp_Int == 24 ) begin
                                        FB_Reg_Up[23:16] = SI_Reg[7:0];
                                end
                                else if ( Tmp_Int == 32 ) begin
                                        FB_Reg_Up[31:24] = SI_Reg[7:0];
                                end
                        end
                    end  
                end
            end  // end forever
        end
    endtask // write_FB_register

    /*----------------------------------------------------------------------*/
    /*  Description: Execute erase Fast Boot register                       */
    /*----------------------------------------------------------------------*/
    task erase_FB_register;
        begin
            Secur_Reg[6] = 1'b0;
            Status_Reg[0] = 1'b1;
            #tSE;
            FB_Reg = 32'hffff_ffff;
            //WIP : write in process Bit
            Status_Reg[0] = 1'b0;
            //WEL:Write Enable Latch
            Status_Reg[1] = 1'b0;
            Secur_Reg[6] = 1'b0;
            ESFBR_Mode = 1'b0;
        end
    endtask // erase_FB_register


    /*----------------------------------------------------------------------*/
    /*  Description: Execute Read Fast Boot Register                        */
    /*----------------------------------------------------------------------*/
    task read_FB_register;
        reg [31:0] Dummy_FB;
        integer Dummy_Count;
        begin
            Dummy_Count = 32;
            Dummy_FB = { FB_Reg [7:0], FB_Reg [15:8], FB_Reg [23:16], FB_Reg [31:24] };
            forever begin
                @ ( negedge SCLK or posedge CS_INT );
                if ( CS_INT == 1'b1 ) begin
                    disable read_FB_register;
                end
                else begin
                    SO_OUT_EN =  1'b1;
                    SI_IN_EN  =  1'b0;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        SIO1_Reg <= Dummy_FB[Dummy_Count];
                    end
                    else begin
                        Dummy_Count = 31;
                        SIO1_Reg <= Dummy_FB[Dummy_Count];
                    end
                end
            end // end forever
        end
    endtask // read_FB_register

    /*----------------------------------------------------------------------*/
    /*  Description: define a block erase task                              */
    /*               52 AD1 AD2 AD3                                         */
    /*----------------------------------------------------------------------*/
    task block_erase_32k;
        integer i, i_tmp;
        //time ERS_Time;
        integer Start_Add;
        integer End_Add;
        begin
            Block       =  Address[A_MSB:16];
            Block2      =  Address[A_MSB:15];
            Start_Add   = (Address[A_MSB:15]<<15) + 16'h0;
            End_Add     = (Address[A_MSB:15]<<15) + 16'h7fff;
            //WIP : write in process Bit
            Status_Reg[0] =  1'b1;
            Secur_Reg[6]  =  1'b0;
            if ( write_protect(Address) == 1'b0 )  begin
               for( i = Start_Add; i <= End_Add; i = i + 1 )
               begin
                   ARRAY[i] = 8'hxx;
               end
               ERS_Time = ERS_Count_BE32K;
               fork
                   er_timer;
                   begin
                       for( i = 0; i < ERS_Time; i = i + 1 ) begin
                           @ ( negedge ERS_CLK or posedge Susp_Trig );
                           if ( Susp_Trig == 1'b1 ) begin
                               if( Susp_Ready == 0 ) i = i_tmp;
                               i_tmp = i;
                               wait( Resume_Trig );
                               $display ( $time, " Resume BE32K Erase ..." );
                           end
                       end
                       //#tBE32 ;
                       for( i = Start_Add; i <= End_Add; i = i + 1 )
                       begin
                           ARRAY[i] = 8'hff;
                       end
                       disable er_timer;
                       disable resume_write;
                       Susp_Ready = 1'b1;
                   end
               join
               //WIP : write in process Bit
               Status_Reg[0] =  1'b0;//WIP
               //WEL : write enable latch
               Status_Reg[1] =  1'b0;//WEL
               BE_Mode = 1'b0;
               BE32K_Mode = 1'b0;
            end
            else begin
                Secur_Reg[6]  = 1'b1;
                Status_Reg[0] = 1'b0;//WIP
                Status_Reg[1] = 1'b0;//WEL
                BE_Mode = 1'b0;
                BE32K_Mode = 1'b0;
            end
        end
    endtask // block_erase_32k

    /*----------------------------------------------------------------------*/
    /*  Description: define an suspend task                                 */
    /*----------------------------------------------------------------------*/
    task suspend_write;
        begin
            disable resume_write;
            Susp_Ready = 1'b1;

            if ( Pgm_Mode ) begin
                Susp_Trig = 1;
                During_Susp_Wait = 1'b1;
                #tPSL;
                $display ( $time, " Suspend Program ..." );
                Secur_Reg[2]  = 1'b1;//PSB
                Status_Reg[0] = 1'b0;//WIP
                Status_Reg[1] = 1'b0;//WEL
                WR2Susp = 0;
                During_Susp_Wait = 1'b0;
            end
            else if ( Ers_Mode ) begin
                Susp_Trig = 1;
                During_Susp_Wait = 1'b1;
                #tESL;
                $display ( $time, " Suspend Erase ..." );
                Secur_Reg[3]  = 1'b1;//ESB
                Status_Reg[0] = 1'b0;//WIP
                Status_Reg[1] = 1'b0;//WEL
                WR2Susp = 0;
                During_Susp_Wait = 1'b0;
            end
        end
    endtask // suspend_write

    /*----------------------------------------------------------------------*/
    /*  Description: define an resume task                                  */
    /*----------------------------------------------------------------------*/
    task resume_write;
        begin
            if ( Pgm_Mode ) begin
                Susp_Ready    = 1'b0;
                Status_Reg[0] = 1'b1;//WIP
                Status_Reg[1] = 1'b1;//WEL
                Secur_Reg[2]  = 1'b0;//PSB
                Resume_Trig   = 1;
                #tPRS;
                Susp_Ready    = 1'b1;
            end
            else if ( Ers_Mode ) begin
                Susp_Ready    = 1'b0;
                Status_Reg[0] = 1'b1;//WIP
                Status_Reg[1] = 1'b1;//WEL
                Secur_Reg[3]  = 1'b0;//ESB
                Resume_Trig   = 1;
                #tERS;
                Susp_Ready    = 1'b1;
            end
        end
    endtask // resume_write

    /*----------------------------------------------------------------------*/
    /*  Description: define a timer to count erase time                     */
    /*----------------------------------------------------------------------*/
    task er_timer;
        begin
            ERS_CLK = 1'b0;
            forever
                begin
                    #(Clock*500) ERS_CLK = ~ERS_CLK;    // erase timer period is 50us
                end
        end
    endtask // er_timer

    /*----------------------------------------------------------------------*/
    /*  Description: define a block erase task                              */
    /*               D8 AD1 AD2 AD3                                         */
    /*----------------------------------------------------------------------*/
    task block_erase;
        integer i, i_tmp;
        //time ERS_Time;
        integer Start_Add;
        integer End_Add;
        begin
            Block       =  Address[A_MSB:16];
            Block2      =  Address[A_MSB:15];
            Start_Add   = (Address[A_MSB:16]<<16) + 16'h0;
            End_Add     = (Address[A_MSB:16]<<16) + 16'hffff;
            //WIP : write in process Bit
            Status_Reg[0] =  1'b1;
            Secur_Reg[6]  =  1'b0;
            if ( write_protect(Address) == 1'b0 ) begin
               for( i = Start_Add; i <= End_Add; i = i + 1 )
               begin
                   ARRAY[i] = 8'hxx;
               end
               ERS_Time = ERS_Count_BE;
               fork
                   er_timer;
                   begin
                       for( i = 0; i < ERS_Time; i = i + 1 ) begin
                           @ ( negedge ERS_CLK or posedge Susp_Trig );
                           if ( Susp_Trig == 1'b1 ) begin
                               if( Susp_Ready == 0 ) i = i_tmp;
                               i_tmp = i;
                               wait( Resume_Trig );
                               $display ( $time, " Resume BE Erase ..." );
                           end
                       end
                       //#tBE ;
                       for( i = Start_Add; i <= End_Add; i = i + 1 )
                       begin
                           ARRAY[i] = 8'hff;
                       end
                       disable er_timer;
                       disable resume_write;
                       Susp_Ready = 1'b1;
                   end
               join
            end
            else begin
                Secur_Reg[6] = 1'b1;
            end   
                //WIP : write in process Bit
                Status_Reg[0] =  1'b0;//WIP
                //WEL : write enable latch
                Status_Reg[1] =  1'b0;//WEL
                BE_Mode = 1'b0;
                BE64K_Mode = 1'b0;
        end
    endtask // block_erase

    /*----------------------------------------------------------------------*/
    /*  Description: define a sector 4k erase task                          */
    /*               20 AD1 AD2 AD3                                         */
    /*----------------------------------------------------------------------*/
    task sector_erase_4k;
        integer i, i_tmp;
        //time ERS_Time;
        integer Start_Add;
        integer End_Add;
        begin
            Sector      =  Address[A_MSB:12]; 
            Start_Add   = (Address[A_MSB:12]<<12) + 12'h000;
            End_Add     = (Address[A_MSB:12]<<12) + 12'hfff;          
            //WIP : write in process Bit
            Status_Reg[0] =  1'b1;
            Secur_Reg[6]  =  1'b0;
            if ( write_protect(Address) == 1'b0 ) begin
               for( i = Start_Add; i <= End_Add; i = i + 1 )
               begin
                   ARRAY[i] = 8'hxx;
               end
               ERS_Time = ERS_Count_SE;
               fork
                   er_timer;
                   begin
                       for( i = 0; i < ERS_Time; i = i + 1 ) begin
                           @ ( negedge ERS_CLK or posedge Susp_Trig );
                           if ( Susp_Trig == 1'b1 ) begin
                               if( Susp_Ready == 0 ) i = i_tmp;
                               i_tmp = i;
                               wait( Resume_Trig );
                               $display ( $time, " Resume SE Erase ..." );
                           end
                       end
                       for( i = Start_Add; i <= End_Add; i = i + 1 )
                       begin
                           ARRAY[i] = 8'hff;
                       end
                       disable er_timer;
                       disable resume_write;
                       Susp_Ready = 1'b1;
                   end
               join
            end
            else begin
                Secur_Reg[6] = 1'b1;
            end
                //WIP : write in process Bit
                Status_Reg[0] = 1'b0;//WIP
                //WEL : write enable latch
                Status_Reg[1] = 1'b0;//WEL
                SE_4K_Mode = 1'b0;
         end
    endtask // sector_erase_4k
    
    /*----------------------------------------------------------------------*/
    /*  Description: define a chip erase task                               */
    /*               60(C7)                                                 */
    /*----------------------------------------------------------------------*/
    task chip_erase;
        reg [A_MSB:0] Address_Int;
        integer i, j, k;
        begin
            Address_Int = Address;
            Status_Reg[0] =  1'b1;
            Secur_Reg[6]  =  1'b0;
            if ( Dis_CE == 1'b1 ) begin
                Secur_Reg[6] = 1'b1;
            end
            else begin
                for ( i = 0;i<tCE/100;i = i + 1) begin
                    #100_000_000;
                end
                    for( i = 0; i <Block_NUM; i = i+1 ) begin
                        Address_Int = (i<<16) + 16'h0;
                        Start_Add = (i<<16) + 16'h0;
                        End_Add   = (i<<16) + 16'hffff;
                        for( j = Start_Add; j <=End_Add; j = j + 1 ) begin
                                ARRAY[j] =  8'hff;
                        end
                    end
            end
            //WIP : write in process Bit
            Status_Reg[0] = 1'b0;//WIP
            //WEL : write enable latch
            Status_Reg[1] = 1'b0;//WEL
            CE_Mode = 1'b0;
        end
    endtask // chip_erase       

    /*----------------------------------------------------------------------*/
    /*  Description: define a page program task                             */
    /*               02 AD1 AD2 AD3                                         */
    /*----------------------------------------------------------------------*/
    task page_program;
        input  [A_MSB:0]  Address;
        reg    [7:0]      Offset;
        integer Dummy_Count, Tmp_Int, i;
        begin
            Dummy_Count = Buffer_Num;    // page size
            Tmp_Int = 0;
            Offset  = Address[7:0];
            /*------------------------------------------------*/
            /*  Store 256 bytes into a temp buffer - Dummy_A  */
            /*------------------------------------------------*/
            for (i = 0; i < Dummy_Count ; i = i + 1 ) begin
                Dummy_A[i]  = 8'hff;
            end
            forever begin
                @ ( posedge SCLK or posedge CS_INT );
                if ( CS_INT == 1'b1 ) begin
                    if ( (Tmp_Int % 8 !== 0) || (Tmp_Int == 1'b0) ) begin
                        PP_4XIO_Mode = 0;
                        PP_1XIO_Mode = 0;
                        disable page_program;
                    end
                    else begin
                        if ( Tmp_Int > 8 )
                            Byte_PGM_Mode = 1'b0;
                        else 
                            Byte_PGM_Mode = 1'b1;
                        update_array ( Address );
                    end
                    disable page_program;
                end
                else begin  // count how many Bits been shifted
                    Tmp_Int = ( PP_4XIO_Mode | ENQUAD ) ? Tmp_Int + 4 : Tmp_Int + 1;
                    if ( Tmp_Int % 8 == 0) begin
                        #1;
                        Dummy_A[Offset] = SI_Reg [7:0];
                        Offset = Offset + 1;   
                        Offset = Offset[7:0];   
                    end  
                end
            end  // end forever
        end
    endtask // page_program

    
    /*----------------------------------------------------------------------*/
    /*  Description: define a read electronic ID (RES)                      */
    /*               AB X X X                                               */
    /*----------------------------------------------------------------------*/
    task read_electronic_id;
        reg  [7:0] Dummy_ID;
        integer Dummy_Count;
        begin
                Dummy_Count = ENQUAD ? 2 : 8;
                if (ENQUAD) begin
                        dummy_cycle(5);
                end
                else begin
                        dummy_cycle(23);
                end
                Dummy_ID = ID_Device;
                dummy_cycle(1);

                forever begin
                        @ ( negedge SCLK or posedge CS_INT );
                        if ( CS_INT == 1'b1 ) begin
                                disable read_electronic_id;
                        end 
                        else begin  
                                if (ENQUAD) begin
                                        SI_OUT_EN    = 1'b1;
                                        WP_OUT_EN    = 1'b1;
                                        SIO3_OUT_EN  = 1'b1;
                                end
                                SO_OUT_EN = 1'b1;
                                SO_IN_EN  = 1'b0;
                                SI_IN_EN  = 1'b0;
                                WP_IN_EN  = 1'b0;
                                SIO3_IN_EN= 1'b0;
                                if ( Dummy_Count ) begin
                                        Dummy_Count = Dummy_Count - 1;
                                        if (ENQUAD) begin
                                                {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_Count ? Dummy_ID[7:4] : Dummy_ID[3:0];
                                        end
                                        else begin
                                                SIO1_Reg <= Dummy_ID[Dummy_Count];
                                        end
                                end
                                else begin
                                        if (ENQUAD) begin
                                                Dummy_Count = 1;
                                                {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_ID[7:4];
                                        end
                                        else begin
                                                Dummy_Count = 7;
                                                SIO1_Reg <= Dummy_ID[Dummy_Count];
                                        end
                                end
                        end
                end // end forever       
        end
    endtask // read_electronic_id
            
    /*----------------------------------------------------------------------*/
    /*  Description: define a read electronic manufacturer & device ID      */
    /*----------------------------------------------------------------------*/
    task read_electronic_manufacturer_device_id;
        reg  [15:0] Dummy_ID;
        integer Dummy_Count;
        begin
                Dummy_Count = 16;
                dummy_cycle(24);
                #1;
                if ( Address[0] == 1'b0 ) begin
                        Dummy_ID = {ID_MXIC,ID_Device};
                end
                else begin
                        Dummy_ID = {ID_Device,ID_MXIC};
                end
                forever begin
                        @ ( negedge SCLK or posedge CS_INT );
                        if ( CS_INT == 1'b1 ) begin
                                disable read_electronic_manufacturer_device_id;
                        end
                        else begin
                                SO_OUT_EN =  1'b1;
                                SI_IN_EN  =  1'b0;
                                if ( Dummy_Count ) begin
                                        Dummy_Count = Dummy_Count - 1;
                                        SIO1_Reg <= Dummy_ID[Dummy_Count];
                                end
                                else begin
                                        Dummy_Count = 15;
                                        SIO1_Reg <= Dummy_ID[Dummy_Count];
                                end
                        end
                end     // end forever
        end
    endtask // read_electronic_manufacturer_device_id

    /*----------------------------------------------------------------------*/
    /*  Description: define a program chip task                             */
    /*  INPUT:address                                                       */
    /*----------------------------------------------------------------------*/
    task update_array;
        input [A_MSB:0] Address;
        integer Dummy_Count, i, i_tmp;
        integer program_time;
        reg [7:0]  ori [0:Buffer_Num-1];
        begin
            Dummy_Count = Buffer_Num;
            Address = { Address [A_MSB:8], 8'h0 };
            program_time = (Byte_PGM_Mode) ? tBP : tPP;
            Status_Reg[0]= 1'b1;
            Secur_Reg[5] = 1'b0;
            if ( write_protect(Address) == 1'b0 && add_in_erase(Address) == 1'b0 ) begin
                for ( i = 0; i < Dummy_Count; i = i + 1 ) begin
                    if ( Secur_Mode == 1'b1) begin
                        ori[i] = Secur_ARRAY[Address + i];
                        Secur_ARRAY[Address + i] = Secur_ARRAY[Address + i] & 8'bx;
                    end
                    else begin
                        ori[i] = ARRAY[Address + i];
                        ARRAY[Address+ i] = ARRAY[Address + i] & 8'bx;
                    end
                end
                fork
                    pg_timer;
                    begin
                        for( i = 0; i*2 < program_time; i = i + 1 ) begin
                            @ ( negedge PGM_CLK or posedge Susp_Trig );
                            if ( Susp_Trig == 1'b1 ) begin
                                if( Susp_Ready == 0 ) i = i_tmp;
                                i_tmp = i;
                                wait( Resume_Trig );
                                $display ( $time, " Resume program ..." );
                            end
                        end
                        //#program_time ;
                        for ( i = 0; i < Dummy_Count; i = i + 1 ) begin
                            if ( Secur_Mode == 1'b1)
                                Secur_ARRAY[Address + i] = ori[i] & Dummy_A[i];
                            else
                                ARRAY[Address+ i] = ori[i] & Dummy_A[i];
                        end
                        disable pg_timer;
                        disable resume_write;
                        Susp_Ready = 1'b1;
                    end
                join
            end
            else begin
                Secur_Reg[5] = 1'b1;
            end
            Status_Reg[0] = 1'b0;
            Status_Reg[1] = 1'b0;
            PP_4XIO_Mode = 1'b0;
            PP_1XIO_Mode = 1'b0;
            Byte_PGM_Mode = 1'b0;
        end
    endtask // update_array

    /*----------------------------------------------------------------------*/
    /*Description: find out whether the address is selected for erase       */
    /*----------------------------------------------------------------------*/
    function add_in_erase;
        input [A_MSB:0] Address;
        begin
            if( Secur_Mode == 1'b0 ) begin
                if (( ERS_Time == ERS_Count_BE32K && Address[A_MSB:15] == Block2 && ESB ) ||
                   ( ERS_Time == ERS_Count_BE && Address[A_MSB:16] == Block && ESB ) ||
                   ( ERS_Time == ERS_Count_SE && Address[A_MSB:12] == Sector && ESB ) ) begin
                    add_in_erase = 1'b1;
                    $display ( $time," Failed programing,address is in erase" );
                end
                else begin
                    add_in_erase = 1'b0;
                end
            end
            else if( Secur_Mode == 1'b1 ) begin
                    add_in_erase = 1'b0;
            end
        end
    endfunction // add_in_erase


    /*----------------------------------------------------------------------*/
    /*  Description: define a timer to count program time                   */
    /*----------------------------------------------------------------------*/
    task pg_timer;
        begin
            PGM_CLK = 1'b0;
            forever
                begin
                    #1 PGM_CLK = ~PGM_CLK;    // program timer period is 2ns
                end
        end
    endtask // pg_timer

    /*----------------------------------------------------------------------*/
    /*  Description: define a enter secured OTP task                        */
    /*----------------------------------------------------------------------*/
    task enter_secured_otp;
        begin
            //$display( $time, " Enter secured OTP mode  = %b",  Secur_Mode );
            Secur_Mode= 1;
            //$display( $time, " New Enter  secured OTP mode  = %b",  Secur_Mode );
        end
    endtask // enter_secured_otp

    /*----------------------------------------------------------------------*/
    /*  Description: define a exit secured OTP task                         */
    /*----------------------------------------------------------------------*/
    task exit_secured_otp;
        begin
            //$display( $time, " Enter secured OTP mode  = %b",  Secur_Mode );
            Secur_Mode = 0;
            //$display( $time,  " New Enter secured OTP mode  = %b",  Secur_Mode );
        end
    endtask

    /*----------------------------------------------------------------------*/
    /*  Description: Execute Reading Security Register                      */
    /*----------------------------------------------------------------------*/
    task read_Secur_Register;
        integer Dummy_Count;
        begin
            if (ENQUAD) begin
                Dummy_Count = 2;
            end
            else begin
                Dummy_Count = 8;
            end
            forever @ ( negedge SCLK or posedge CS_INT ) begin // output security register info
                if ( CS_INT == 1 ) begin
                    disable     read_Secur_Register;
                end
                else  begin   
                    if (ENQUAD) begin
                        SI_OUT_EN    = 1'b1;
                        WP_OUT_EN    = 1'b1;
                        SIO3_OUT_EN  = 1'b1;
                    end
                    SO_OUT_EN = 1'b1;
                    SO_IN_EN  = 1'b0;
                    SI_IN_EN  = 1'b0;
                    WP_IN_EN  = 1'b0;
                    SIO3_IN_EN= 1'b0;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        if (ENQUAD) begin
                            {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_Count ?
                                                          Secur_Reg[7:4] : Secur_Reg[3:0];
                        end
                        else begin
                            SIO1_Reg    <= Secur_Reg[Dummy_Count];
                        end
                    end
                    else begin
                        if (ENQUAD) begin
                            Dummy_Count = 1;
                            {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Secur_Reg[7:4];
                        end
                        else begin
                            Dummy_Count = 7;
                            SIO1_Reg    <= Secur_Reg[Dummy_Count];
                        end
                    end          
                end      
            end
        end  
    endtask // read_Secur_Register

    /*----------------------------------------------------------------------*/
    /*  Description: Execute Write Security Register                        */
    /*----------------------------------------------------------------------*/
    task write_secur_register;
        begin
            WRSCUR_Mode = 1'b1;
            Status_Reg[0] = 1'b1;
            #tBP; 
            WRSCUR_Mode = 1'b0;
            Secur_Reg [1] = 1'b1;
            Status_Reg[0] = 1'b0;
            Status_Reg[1] = 1'b0;
        end
    endtask // write_secur_register

    /*----------------------------------------------------------------------*/
    /*  Description: Execute Reading Extended Address Register              */
    /*----------------------------------------------------------------------*/
    task read_EA_Register;
        integer Dummy_Count;
        begin
            if (ENQUAD) begin
                Dummy_Count = 2;
            end
            else begin
                Dummy_Count = 8;
            end
            forever @ ( negedge SCLK or posedge CS_INT ) begin // output Reading Extended register info
                if ( CS_INT == 1 ) begin
                    disable     read_EA_Register;
                end
                else  begin   
                    if (ENQUAD) begin
                        SI_OUT_EN    = 1'b1;
                        WP_OUT_EN    = 1'b1;
                        SIO3_OUT_EN  = 1'b1;
                    end
                    SO_OUT_EN = 1'b1;
                    SO_IN_EN  = 1'b0;
                    SI_IN_EN  = 1'b0;
                    WP_IN_EN  = 1'b0;
                    SIO3_IN_EN= 1'b0;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        if (ENQUAD) begin
                            {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_Count ?
                                                          EA_Reg[7:4] : EA_Reg[3:0];
                        end
                        else begin
                            SIO1_Reg    <= EA_Reg[Dummy_Count];
                        end
                    end
                    else begin
                        if (ENQUAD) begin
                            Dummy_Count = 1;
                            {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= EA_Reg[7:4];
                        end
                        else begin
                            Dummy_Count = 7;
                            SIO1_Reg    <= EA_Reg[Dummy_Count];
                        end
                    end          
                end      
            end
        end  
    endtask // read_EA_Register

    /*----------------------------------------------------------------------*/
    /*  Description: Execute Write Extended Address Register                */
    /*----------------------------------------------------------------------*/
    task write_ea_register;
        reg [7:0] EA_Reg_Up;
        begin
            WREAR_Mode       = 1'b1;
            //$display( $time, " Old Extended Address Register = %b", EA_Reg );
            EA_Reg_Up = SI_Reg[7:0];

            Status_Reg[0]   = 1'b1;
            #tWREAR;
            EA_Reg[0]   =  EA_Reg_Up[0];
            EA_Reg[7:1] =  7'b0000000;

            //WIP:Write Enable Latch
            Status_Reg[0]   = 1'b0;
            //WEL:Write Enable Latch
            Status_Reg[1]   = 1'b0;
            WREAR_Mode       = 1'b0;
        end
     endtask // write_ea_register

    /*----------------------------------------------------------------------*/
    /*  Description: Execute 2X IO Read Mode                                */
    /*----------------------------------------------------------------------*/
   task read_2xio;
        reg  [7:0]  OUT_Buf;
        integer     Dummy_Count;
        begin
            Dummy_Count=4;
            SI_IN_EN = 1'b1;
            SO_IN_EN = 1'b1;
            SI_OUT_EN = 1'b0;
            SO_OUT_EN = 1'b0;
            if ( !CR[5] && !ADD_4B_Mode )
                    dummy_cycle(12); // for address
            else if ( CR[5] || ADD_4B_Mode )
                    dummy_cycle(16); // for address

            if ( CR[7:6] == 2'b00 )
                    dummy_cycle(4);
            else if ( CR[7:6] == 2'b01 )
                    dummy_cycle(6);
            else if ( CR[7:6] == 2'b10 )
                    dummy_cycle(8);
            else if ( CR[7:6] == 2'b11 )
                    dummy_cycle(10);

            #1;
            read_array(Address, OUT_Buf);
          
            forever @ ( negedge SCLK or  posedge CS_INT ) begin
                if ( CS_INT == 1'b1 ) begin
                    disable read_2xio;
                end
                else begin
                    Read_Mode   = 1'b1;
                    SO_OUT_EN   = 1'b1;
                    SI_OUT_EN   = 1'b1;
                    SI_IN_EN    = 1'b0;
                    SO_IN_EN    = 1'b0;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        if ( Dummy_Count == 3 )
                                {SIO1_Reg, SIO0_Reg} <= OUT_Buf[7:6];
                        else if ( Dummy_Count == 2 )
                                {SIO1_Reg, SIO0_Reg} <= OUT_Buf[5:4];
                        else if ( Dummy_Count == 1 )
                                {SIO1_Reg, SIO0_Reg} <= OUT_Buf[3:2];
                        else if ( Dummy_Count == 0 )
                                {SIO1_Reg, SIO0_Reg} <= OUT_Buf[1:0];
                    end
                    else begin
                        Address = Address + 1;
                        load_address(Address);
                        read_array(Address, OUT_Buf);
                        Dummy_Count = 3;
                        {SIO1_Reg, SIO0_Reg} <= OUT_Buf[7:6];
                    end
                end
            end//forever  
        end
    endtask // read_2xio

    /*----------------------------------------------------------------------*/
    /*  Description: Execute 4X IO Read Mode                                */
    /*----------------------------------------------------------------------*/
    task read_4xio;
        //reg [A_MSB:0] Address;
        reg [7:0]   OUT_Buf ;
        integer     Dummy_Count;
        begin
            Dummy_Count = 2;
            SI_OUT_EN    = 1'b0;
            SO_OUT_EN    = 1'b0;
            WP_OUT_EN    = 1'b0;
            SIO3_OUT_EN  = 1'b0;
            SI_IN_EN    = 1'b1;
            SO_IN_EN    = 1'b1;
            WP_IN_EN    = 1'b1;
            SIO3_IN_EN   = 1'b1;
            if ( CR[5] || ADD_4B_Mode || CMD_BUS == READ4X4B || (!READ4X_Mode && (CMD_BUS == RSTEN || CMD_BUS == RST) && EN4XIO_Read_Mode == 1'b1) ) begin
                    ADD_4B_Mode = 1'b1;
                    dummy_cycle(8); // for address
            end
            else
                    dummy_cycle(6); // for address

            dummy_cycle(2);
            #1;
            if ( ((SI_Reg[0] === 1'hz) ||
                 (SI_Reg[1] === 1'hz) ||
                 (SI_Reg[2] === 1'hz) ||
                 (SI_Reg[3] === 1'hz) ||
                 (SI_Reg[4] === 1'hz) || 
                 (SI_Reg[5] === 1'hz) ||  
                 (SI_Reg[6] === 1'hz) ||
                 (SI_Reg[7] === 1'hz) ) &&
                 (SFDP_Mode  !== 1) ) begin
                 $display("Warning: Hi-impedance is inhibited for the two clock cycles.");
                 STATE = `BAD_CMD_STATE;
                 disable read_4xio;
            end
            else if ((SI_Reg[0] !== SI_Reg[4]) &&
                 (SI_Reg[1]!= SI_Reg[5]) &&
                 (SI_Reg[2]!= SI_Reg[6]) &&
                 (SI_Reg[3]!= SI_Reg[7]) ) begin
                Set_4XIO_Enhance_Mode = 1'b1;
            end
            else  begin 
                Set_4XIO_Enhance_Mode = 1'b0;
            end
            if ( SFDP_Mode == 1 )
                dummy_cycle(6);
            else if ( CR[7:6] == 2'b00 )
                dummy_cycle(4);
            else if ( CR[7:6] == 2'b01 )
                dummy_cycle(2);
            else if ( CR[7:6] == 2'b10 )
                dummy_cycle(6);
            else if ( CR[7:6] == 2'b11 )
                dummy_cycle(8);

            read_array(Address, OUT_Buf);


            forever @ ( negedge SCLK or  posedge CS_INT ) begin
                if ( CS_INT == 1'b1 ) begin
                    disable read_4xio;
                end
                  
                else begin
                    SO_OUT_EN   = 1'b1;
                    SI_OUT_EN   = 1'b1;
                    WP_OUT_EN   = 1'b1;
                    SIO3_OUT_EN = 1'b1;
                    SO_IN_EN    = 1'b0;
                    SI_IN_EN    = 1'b0;
                    WP_IN_EN    = 1'b0;
                    SIO3_IN_EN  = 1'b0;
                    Read_Mode  = 1'b1;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_Count ? OUT_Buf[7:4] : OUT_Buf[3:0];
                    end
                    else begin
                        if ( EN_Burst && Burst_Length==8 && Address[2:0]==3'b111 )
                            Address = {Address[A_MSB:3], 3'b000};
                        else if ( EN_Burst && Burst_Length==16 && Address[3:0]==4'b1111 )
                            Address = {Address[A_MSB:4], 4'b0000};
                        else if ( EN_Burst && Burst_Length==32 && Address[4:0]==5'b1_1111 )
                            Address = {Address[A_MSB:5], 5'b0_0000};
                        else if ( EN_Burst && Burst_Length==64 && Address[5:0]==6'b11_1111 )
                            Address = {Address[A_MSB:6], 6'b00_0000};
                        else
                            Address = Address + 1;
                        load_address(Address);
                        read_array(Address, OUT_Buf);
                        Dummy_Count = 1;
                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= OUT_Buf[7:4];
                    end
                end
            end//forever  
        end
    endtask // read_4xio

    /*----------------------------------------------------------------------*/
    /*  Description: define a fast read dual output data task               */
    /*               3B AD1 AD2 AD3 X                                       */
    /*----------------------------------------------------------------------*/
    task fastread_2xio;
        integer Dummy_Count;
        reg  [7:0] OUT_Buf;
        begin
            Dummy_Count = 4 ;
            if ( !CR[5] && !ADD_4B_Mode )
                    dummy_cycle(24); // for address
            else if ( CR[5] || ADD_4B_Mode )
                    dummy_cycle(32); // for address

            if ( CR[7:6] == 2'b00 )
                dummy_cycle(8);
            else if ( CR[7:6] == 2'b01 )
                dummy_cycle(6);
            else if ( CR[7:6] == 2'b10 )
                dummy_cycle(8);
            else if ( CR[7:6] == 2'b11 )
                dummy_cycle(10);

            #1;
            read_array(Address, OUT_Buf);
            forever @ ( negedge SCLK or  posedge CS_INT ) begin
                if ( CS_INT == 1'b1 ) begin
                    disable fastread_2xio;
                end
                else begin
                    Read_Mode= 1'b1;
                    SO_OUT_EN = 1'b1;
                    SI_OUT_EN = 1'b1;
                    SI_IN_EN  = 1'b0;
                    SO_IN_EN  = 1'b0;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        if ( Dummy_Count == 3 )
                                {SIO1_Reg, SIO0_Reg} <= OUT_Buf[7:6];
                        else if ( Dummy_Count == 2 )
                                {SIO1_Reg, SIO0_Reg} <= OUT_Buf[5:4];
                        else if ( Dummy_Count == 1 )
                                {SIO1_Reg, SIO0_Reg} <= OUT_Buf[3:2];
                        else if ( Dummy_Count == 0 )
                                {SIO1_Reg, SIO0_Reg} <= OUT_Buf[1:0];
                    end
                    else begin
                        Address = Address + 1;
                        load_address(Address);
                        read_array(Address, OUT_Buf);
                        Dummy_Count = 3;
                        {SIO1_Reg, SIO0_Reg} <= OUT_Buf[7:6];
                    end
                end
            end//forever  
        end
    endtask // fastread_2xio

    /*----------------------------------------------------------------------*/
    /*  Description: define a fast read quad output data task               */
    /*               6B AD1 AD2 AD3 X                                       */
    /*----------------------------------------------------------------------*/
    task fastread_4xio;
        integer Dummy_Count;
        reg  [7:0]  OUT_Buf;
        begin
            Dummy_Count = 2 ;
            if ( !CR[5] && !ADD_4B_Mode )
                dummy_cycle(24); // for address
            else if ( CR[5] || ADD_4B_Mode )
                dummy_cycle(32); // for address

            if ( CR[7:6] == 2'b00 )
                dummy_cycle(8);
            else if ( CR[7:6] == 2'b01 )
                dummy_cycle(6);
            else if ( CR[7:6] == 2'b10 )
                dummy_cycle(8);
            else if ( CR[7:6] == 2'b11 )
                dummy_cycle(10);

            #1;
            read_array(Address, OUT_Buf);       
            forever @ ( negedge SCLK or  posedge CS_INT ) begin
                if ( CS_INT ==      1'b1 ) begin
                    disable fastread_4xio;
                end
                else begin
                    SI_IN_EN    = 1'b0;
                    SI_OUT_EN   = 1'b1;
                    SO_OUT_EN   = 1'b1;
                    WP_OUT_EN   = 1'b1;
                    SIO3_OUT_EN = 1'b1;
                    if ( Dummy_Count ) begin
                        Dummy_Count = Dummy_Count - 1;
                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= Dummy_Count ? OUT_Buf[7:4] : OUT_Buf[3:0];
                    end
                    else begin
                        Address = Address + 1;
                        load_address(Address);
                        read_array(Address, OUT_Buf);
                        Dummy_Count = 1;
                        {SIO3_Reg, SIO2_Reg, SIO1_Reg, SIO0_Reg} <= OUT_Buf[7:4];
                    end
                end
            end//forever
        end
    endtask // fastread_4xio

    /*----------------------------------------------------------------------*/
    /*  Description: define read array output task                          */
    /*----------------------------------------------------------------------*/
    task read_array;
        input [A_MSB:0] Address;
        output [7:0]    OUT_Buf;
        begin
            if ( Secur_Mode == 1 ) begin
                OUT_Buf = Secur_ARRAY[Address];
            end
            else if ( SFDP_Mode == 1 ) begin
                OUT_Buf = SFDP_ARRAY[Address];
            end
            else begin
                OUT_Buf = ARRAY[Address] ;
            end
        end
    endtask //  read_array

    /*----------------------------------------------------------------------*/
    /*  Description: define read array output task                          */
    /*----------------------------------------------------------------------*/
    task load_address;
        inout [A_MSB:0] Address;
        begin
            if ( Secur_Mode == 1 ) begin
                Address = Address[A_MSB_OTP:0] ;
            end
            else if ( SFDP_Mode == 1 ) begin
                Address = Address[A_MSB_SFDP:0] ;
            end
        end
    endtask //  load_address

    /*----------------------------------------------------------------------*/
    /*  Description: define a write_protect area function                   */
    /*  INPUT: address                                                      */
    /*----------------------------------------------------------------------*/ 
    function write_protect;
        input [A_MSB:0] Address;
        reg [Block_MSB:0] Block;
        begin
            //protect_define
            if( Secur_Mode == 1'b0 ) begin
                Block  =  Address [A_MSB:16];
                  if ( CR[3] == 1'b0 ) begin
                    if (Status_Reg[5:2] == 4'b0000) begin
                        write_protect = 1'b0;
                    end
                    else if (Status_Reg[5:2] == 4'b0001) begin
                        if (Block[Block_MSB:0] > 510 && Block[Block_MSB:0] <= 511) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0010) begin
                        if (Block[Block_MSB:0] >= 510 && Block[Block_MSB:0] <= 511) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end

                    else if (Status_Reg[5:2] == 4'b0011) begin
                        if (Block[Block_MSB:0] >= 508 && Block[Block_MSB:0] <= 511) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0100) begin
                        if (Block[Block_MSB:0] >= 504 && Block[Block_MSB:0] <= 511) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0101) begin
                        if (Block[Block_MSB:0] >= 496 && Block[Block_MSB:0] <= 511) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0110) begin
                        if (Block[Block_MSB:0] >= 480 && Block[Block_MSB:0] <= 511) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0111) begin
                        if (Block[Block_MSB:0] >= 448 && Block[Block_MSB:0] <= 511) begin
                            write_protect = 1'b1;
                        end
                        else begin
                            write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b1000) begin
                        if (Block[Block_MSB:0] >= 384 && Block[Block_MSB:0] <= 511) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b1001) begin
                        if (Block[Block_MSB:0] >= 256 && Block[Block_MSB:0] <= 511) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else
                        write_protect = 1'b1;
                  end
                  else begin
                    if (Status_Reg[5:2] == 4'b0000) begin
                        write_protect = 1'b0;
                    end
                    else if (Status_Reg[5:2] == 4'b0001) begin
                        if (Block[Block_MSB:0] >= 0 && Block[Block_MSB:0] < 1) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0010) begin
                        if (Block[Block_MSB:0] >= 0 && Block[Block_MSB:0] <= 1) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0011) begin
                        if (Block[Block_MSB:0] >= 0 && Block[Block_MSB:0] <= 3) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0100) begin
                        if (Block[Block_MSB:0] >= 0 && Block[Block_MSB:0] <= 7) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0101) begin
                        if (Block[Block_MSB:0] >= 0 && Block[Block_MSB:0] <= 15) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0110) begin
                        if (Block[Block_MSB:0] >= 0 && Block[Block_MSB:0] <= 31) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b0111) begin
                        if (Block[Block_MSB:0] >= 0 && Block[Block_MSB:0] <= 63) begin
                            write_protect = 1'b1;
                        end
                        else begin
                            write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b1000) begin
                        if (Block[Block_MSB:0] >= 0 && Block[Block_MSB:0] <= 127) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else if (Status_Reg[5:2] == 4'b1001) begin
                        if (Block[Block_MSB:0] >= 0 && Block[Block_MSB:0] <= 255) begin
                                write_protect = 1'b1;
                        end
                        else begin
                                write_protect = 1'b0;
                        end
                    end
                    else
                        write_protect = 1'b1;
                  end  
            end
            else if( Secur_Mode == 1'b1 ) begin
                if ( Secur_Reg [1] == 1'b0 && Secur_Reg [0] == 1'b0 ) begin
                    write_protect = 1'b0;
                end
                else begin
                    write_protect = 1'b1;
                end
            end
            else begin
                write_protect = 1'b0;
            end
        end
    endfunction // write_protect


// *============================================================================================== 
// * AC Timing Check Section
// *==============================================================================================
    wire SIO3_EN;
    wire WP_EN;
    assign SIO3_EN = !Status_Reg[6];
    assign WP_EN = !Status_Reg[6] && !ENQUAD && SRWD;

    assign  Write_SHSL = !Read_SHSL;

    wire Read_1XIO_Chk_W;
    assign Read_1XIO_Chk_W = Read_1XIO_Chk;
    wire Read_2XIO_Chk_W_00;
    assign Read_2XIO_Chk_W_00 = Read_2XIO_Chk && CR_00;
    wire Read_2XIO_Chk_W_01;
    assign Read_2XIO_Chk_W_01 = Read_2XIO_Chk && CR_01;
    wire Read_2XIO_Chk_W_10;
    assign Read_2XIO_Chk_W_10 = Read_2XIO_Chk && CR_10;
    wire Read_2XIO_Chk_W_11;
    assign Read_2XIO_Chk_W_11 = Read_2XIO_Chk && CR_11;
    wire Read_4XIO_Chk_W_00;
    assign Read_4XIO_Chk_W_00 = Read_4XIO_Chk && CR_00;
    wire Read_4XIO_Chk_W_01;
    assign Read_4XIO_Chk_W_01 = Read_4XIO_Chk && CR_01;
    wire Read_4XIO_Chk_W_10;
    assign Read_4XIO_Chk_W_10 = Read_4XIO_Chk && CR_10;
    wire Read_4XIO_Chk_W_11;
    assign Read_4XIO_Chk_W_11 = Read_4XIO_Chk && CR_11;
    wire FastRD_1XIO_Chk_W_00;
    assign FastRD_1XIO_Chk_W_00 = FastRD_1XIO_Chk && CR_00;
    wire FastRD_1XIO_Chk_W_01;
    assign FastRD_1XIO_Chk_W_01 = FastRD_1XIO_Chk && CR_01;
    wire FastRD_1XIO_Chk_W_10;
    assign FastRD_1XIO_Chk_W_10 = FastRD_1XIO_Chk && CR_10;
    wire FastRD_1XIO_Chk_W_11;
    assign FastRD_1XIO_Chk_W_11 = FastRD_1XIO_Chk && CR_11;
    wire FastRD_2XIO_Chk_W_00;
    assign FastRD_2XIO_Chk_W_00 = FastRD_2XIO_Chk && CR_00;
    wire FastRD_2XIO_Chk_W_01;
    assign FastRD_2XIO_Chk_W_01 = FastRD_2XIO_Chk && CR_01;
    wire FastRD_2XIO_Chk_W_10;
    assign FastRD_2XIO_Chk_W_10 = FastRD_2XIO_Chk && CR_10;
    wire FastRD_2XIO_Chk_W_11;
    assign FastRD_2XIO_Chk_W_11 = FastRD_2XIO_Chk && CR_11;
    wire FastRD_4XIO_Chk_W_00;
    assign FastRD_4XIO_Chk_W_00 = FastRD_4XIO_Chk && CR_00;
    wire FastRD_4XIO_Chk_W_01;
    assign FastRD_4XIO_Chk_W_01 = FastRD_4XIO_Chk && CR_01;
    wire FastRD_4XIO_Chk_W_10;
    assign FastRD_4XIO_Chk_W_10 = FastRD_4XIO_Chk && CR_10;
    wire FastRD_4XIO_Chk_W_11;
    assign FastRD_4XIO_Chk_W_11 = FastRD_4XIO_Chk && CR_11;
    wire FAST_BOOT_Chk_W_00;
    assign FAST_BOOT_Chk_W_00 = FAST_BOOT_Chk && ( FB_Reg[2:1] === 2'b00 );
    wire FAST_BOOT_Chk_W_01;
    assign FAST_BOOT_Chk_W_01 = FAST_BOOT_Chk && ( FB_Reg[2:1] === 2'b01 );
    wire FAST_BOOT_Chk_W_10;
    assign FAST_BOOT_Chk_W_10 = FAST_BOOT_Chk && ( FB_Reg[2:1] === 2'b10 );
    wire FAST_BOOT_Chk_W_11;
    assign FAST_BOOT_Chk_W_11 = FAST_BOOT_Chk && ( FB_Reg[2:1] === 2'b11 );
    wire tDP_Chk_W;
    assign tDP_Chk_W = tDP_Chk;
    wire tRES1_Chk_W;
    assign tRES1_Chk_W = tRES1_Chk;
    wire tRES2_Chk_W;
    assign tRES2_Chk_W = tRES2_Chk;
    wire PP_4XIO_Chk_W;
    assign PP_4XIO_Chk_W = PP_4XIO_Chk;
    wire Read_SHSL_W;
    assign Read_SHSL_W = Read_SHSL;
    wire SI_IN_EN_W;
    assign SI_IN_EN_W = SI_IN_EN;
    wire SO_IN_EN_W;
    assign SO_IN_EN_W = SO_IN_EN;
    wire WP_IN_EN_W;
    assign WP_IN_EN_W = WP_IN_EN;
    wire SIO3_IN_EN_W;
    assign SIO3_IN_EN_W = SIO3_IN_EN;

    specify
        /*----------------------------------------------------------------------*/
        /*  Timing Check                                                        */
        /*----------------------------------------------------------------------*/
        $period( posedge  SCLK &&& ~CS, tSCLK  );       // SCLK _/~ ->_/~
        $period( negedge  SCLK &&& ~CS, tSCLK  );       // SCLK ~\_ ->~\_
        $period( posedge  SCLK &&& Read_1XIO_Chk_W , tRSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& Read_2XIO_Chk_W_00 , tTSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& Read_2XIO_Chk_W_01  , tTSCLK2 ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& Read_2XIO_Chk_W_10  , tTSCLK2 ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& Read_2XIO_Chk_W_11 , tTSCLK3 ); // SCLK _/~ ->_/~

        $period( posedge  SCLK &&& Read_4XIO_Chk_W_00 , tQSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& Read_4XIO_Chk_W_01 , tQSCLK2 ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& Read_4XIO_Chk_W_10 , tQSCLK3 ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& Read_4XIO_Chk_W_11 , tQSCLK4 ); // SCLK _/~ ->_/~

        $period( posedge  SCLK &&& FastRD_1XIO_Chk_W_00 , tFSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FastRD_1XIO_Chk_W_01 , tFSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FastRD_1XIO_Chk_W_10 , tFSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FastRD_1XIO_Chk_W_11 , tFSCLK2 ); // SCLK _/~ ->_/~


        $period( posedge  SCLK &&& FastRD_2XIO_Chk_W_00 , tFDSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FastRD_2XIO_Chk_W_01 , tFDSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FastRD_2XIO_Chk_W_10 , tFDSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FastRD_2XIO_Chk_W_11 , tFDSCLK2 ); // SCLK _/~ ->_/~


        $period( posedge  SCLK &&& FastRD_4XIO_Chk_W_00 , tFQSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FastRD_4XIO_Chk_W_01 , tFQSCLK2 ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FastRD_4XIO_Chk_W_10 , tFQSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FastRD_4XIO_Chk_W_11 , tFQSCLK3 ); // SCLK _/~ ->_/~

        $period( posedge  SCLK &&& FAST_BOOT_Chk_W_00 , tFBSCLK ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FAST_BOOT_Chk_W_01 , tFBSCLK2 ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FAST_BOOT_Chk_W_10 , tFBSCLK3 ); // SCLK _/~ ->_/~
        $period( posedge  SCLK &&& FAST_BOOT_Chk_W_11 , tFBSCLK4 ); // SCLK _/~ ->_/~

        $width ( posedge  CS  &&& tDP_Chk_W, tDP );       // CS _/~\_
        $width ( posedge  CS  &&& tRES1_Chk_W, tRES1 );   // CS _/~\_
        $width ( posedge  CS  &&& tRES2_Chk_W, tRES2 );   // CS _/~\_

        $width ( posedge  SCLK &&& ~CS, tCH   );       // SCLK _/~~\_
        $width ( negedge  SCLK &&& ~CS, tCL   );       // SCLK ~\__/~
        $width ( posedge  SCLK &&& Read_1XIO_Chk_W, tCH_R   );       // SCLK _/~~\_
        $width ( negedge  SCLK &&& Read_1XIO_Chk_W, tCL_R   );       // SCLK ~\__/~
        $width ( posedge  SCLK &&& PP_4XIO_Chk_W, tCH_4PP   );       // SCLK _/~~\_
        $width ( negedge  SCLK &&& PP_4XIO_Chk_W, tCL_4PP   );       // SCLK ~\__/~

        $width ( posedge  CS  &&& Read_SHSL_W, tSHSL_R );       // CS _/~\_
        $width ( posedge  CS  &&& Write_SHSL, tSHSL_W );// CS _/~\_
        $setup ( SI &&& ~CS, posedge SCLK &&& SI_IN_EN_W,  tDVCH );
        $hold  ( posedge SCLK &&& SI_IN_EN_W, SI &&& ~CS,  tCHDX );

        $setup ( SO &&& ~CS, posedge SCLK &&& SO_IN_EN_W,  tDVCH );
        $hold  ( posedge SCLK &&& SO_IN_EN_W, SO &&& ~CS,  tCHDX );
        $setup ( WP &&& ~CS, posedge SCLK &&& WP_IN_EN_W,  tDVCH );
        $hold  ( posedge SCLK &&& WP_IN_EN_W, WP &&& ~CS,  tCHDX );

        $setup ( SIO3 &&& ~CS, posedge SCLK &&& SIO3_IN_EN_W,  tDVCH );
        $hold  ( posedge SCLK &&& SIO3_IN_EN_W, SIO3 &&& ~CS,  tCHDX );

        $setup    ( negedge CS, posedge SCLK &&& ~CS, tSLCH );
        $hold     ( posedge SCLK &&& ~CS, posedge CS, tCHSH );
     
        $setup    ( posedge CS, posedge SCLK &&& CS, tSHCH );
        $hold     ( posedge SCLK &&& CS, negedge CS, tCHSL );

        $setup ( posedge WP &&& WP_EN, negedge CS,  tWHSL );
        $hold  ( posedge CS, negedge WP &&& WP_EN,  tSHWL );

        $width ( negedge  RESETB_INT, tRLRH   );      // RESET ~\__/~
        $setup ( posedge CS, negedge RESETB_INT ,  tRS );
        $hold  ( negedge RESETB_INT, posedge CS ,  tRH );
        $hold  ( posedge  RESETB_INT, negedge CS, tRHSL );

     endspecify

    integer AC_Check_File;
    // timing check module 
    initial 
    begin 
        AC_Check_File= $fopen ("ac_check.err" );    
    end

    realtime  T_CS_P , T_CS_N;
    realtime  T_WP_P , T_WP_N;
    realtime  T_SCLK_P , T_SCLK_N;
    realtime  T_SIO3_P , T_SIO3_N;
    realtime  T_SI;
    realtime  T_SO;
    realtime  T_WP;
    realtime  T_SIO3;
    realtime  T_RESET_N, T_RESET_P;                    

    initial 
    begin
        T_CS_P = 0; 
        T_CS_N = 0;
        T_WP_P = 0;  
        T_WP_N = 0;
        T_SCLK_P = 0;  
        T_SCLK_N = 0;
        T_SIO3_P = 0;  
        T_SIO3_N = 0;
        T_SI = 0;
        T_SO = 0;
        T_WP = 0;
        T_SIO3 = 0;
        T_RESET_N = 0;
        T_RESET_P = 0;                    
    end

    always @ ( posedge SCLK ) begin
        //tSCLK
        if ( $realtime - T_SCLK_P < tSCLK && $realtime > 0 && ~CS ) 
            $fwrite (AC_Check_File, "Clock Frequence for except READ instruction fSCLK =%f Mhz, fSCLK timing violation at %f \n", fSCLK, $realtime );
        //fRSCLK
        if ( $realtime - T_SCLK_P < tRSCLK && Read_1XIO_Chk && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for READ instruction fRSCLK =%f Mhz, fRSCLK timing violation at %f \n", fRSCLK, $realtime );
        //fTSCLK
        if ( $realtime - T_SCLK_P < tTSCLK && Read_2XIO_Chk && CR_00 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for 2XI/O instruction fTSCLK =%f Mhz, fTSCLK timing violation at %f \n", fTSCLK, $realtime );
        //fTSCLK2
        if ( $realtime - T_SCLK_P < tTSCLK2 && Read_2XIO_Chk && ( CR_01 || CR_10 ) && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for 2XI/O instruction fTSCLK =%f Mhz, fTSCLK timing violation at %f \n", fTSCLK2, $realtime );
        //fTSCLK3
        if ( $realtime - T_SCLK_P < tTSCLK3 && Read_2XIO_Chk && CR_11 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for 2XI/O instruction fTSCLK =%f Mhz, fTSCLK timing violation at %f \n", fTSCLK3, $realtime );
        //fQSCLK
        if ( $realtime - T_SCLK_P < tQSCLK && Read_4XIO_Chk && CR_00 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for 4XI/O instruction fQSCLK =%f Mhz, fQSCLK timing violation at %f \n", fQSCLK, $realtime );
        //fQSCLK2
        if ( $realtime - T_SCLK_P < tQSCLK2 && Read_4XIO_Chk && CR_01 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for 4XI/O instruction fQSCLK =%f Mhz, fQSCLK timing violation at %f \n", fQSCLK2, $realtime );
        //fQSCLK3
        if ( $realtime - T_SCLK_P < tQSCLK3 && Read_4XIO_Chk && CR_10 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for 4XI/O instruction fQSCLK =%f Mhz, fQSCLK timing violation at %f \n", fQSCLK3, $realtime );
        //fQSCLK4
        if ( $realtime - T_SCLK_P < tQSCLK4 && Read_4XIO_Chk && CR_11 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for 4XI/O instruction fQSCLK =%f Mhz, fQSCLK timing violation at %f \n", fQSCLK4, $realtime );
        //fFSCLK
        if ( $realtime - T_SCLK_P < tFSCLK && FastRD_1XIO_Chk && ( CR_00 || CR_01 || CR_10 ) && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for Fast 1XI/O instruction fFSCLK =%f Mhz, fFSCLK timing violation at %f \n", fFSCLK, $realtime );
        //fFSCLK2
        if ( $realtime - T_SCLK_P < tFSCLK2 && FastRD_1XIO_Chk && CR_11 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for Fast 1XI/O instruction fFSCLK =%f Mhz, fFSCLK timing violation at %f \n", fFSCLK2, $realtime );
        //fFDSCLK
        if ( $realtime - T_SCLK_P < tFDSCLK && FastRD_2XIO_Chk && ( CR_00 || CR_01 || CR_10 ) && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for Fast 2XO instruction fFDSCLK =%f Mhz, fFDSCLK timing violation at %f \n", fFDSCLK, $realtime );
        //fFDSCLK2
        if ( $realtime - T_SCLK_P < tFDSCLK2 && FastRD_2XIO_Chk && CR_11 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for Fast 2XO instruction fFDSCLK =%f Mhz, fFDSCLK timing violation at %f \n", fFDSCLK2, $realtime );
        //fFQSCLK
        if ( $realtime - T_SCLK_P < tFQSCLK && FastRD_4XIO_Chk && ( CR_00 || CR_10 ) && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for Fast 4XO instruction fFQSCLK =%f Mhz, fFQSCLK timing violation at %f \n", fFQSCLK, $realtime );
        //fFQSCLK2
        if ( $realtime - T_SCLK_P < tFQSCLK2 && FastRD_4XIO_Chk && CR_01 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for Fast 4XO instruction fFQSCLK =%f Mhz, fFQSCLK timing violation at %f \n", fFQSCLK2, $realtime );
        //fFQSCLK3
        if ( $realtime - T_SCLK_P < tFQSCLK3 && FastRD_4XIO_Chk && CR_11 && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for Fast 4XO instruction fFQSCLK =%f Mhz, fFQSCLK timing violation at %f \n", fFQSCLK3, $realtime );
        //fFBSCLK
        if ( $realtime - T_SCLK_P < tFBSCLK && FAST_BOOT_Chk && ( FB_Reg[2:1] == 2'b00 ) && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for fast boot instruction fFBSCLK =%f Mhz, fFBSCLK timing violation at %f \n", fFBSCLK, $realtime );
        //fFBSCLK2
        if ( $realtime - T_SCLK_P < tFBSCLK2 && FAST_BOOT_Chk && ( FB_Reg[2:1] == 2'b01 ) && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for fast boot instruction fFBSCLK =%f Mhz, fFBSCLK timing violation at %f \n", fFBSCLK2, $realtime );
        //fFBSCLK3
        if ( $realtime - T_SCLK_P < tFBSCLK3 && FAST_BOOT_Chk && ( FB_Reg[2:1] == 2'b10 ) && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for fast boot instruction fFBSCLK =%f Mhz, fFBSCLK timing violation at %f \n", fFBSCLK3, $realtime );
        //fFBSCLK4
        if ( $realtime - T_SCLK_P < tFBSCLK4 && FAST_BOOT_Chk && ( FB_Reg[2:1] == 2'b11 ) && $realtime > 0 && ~CS )
            $fwrite (AC_Check_File, "Clock Frequence for fast boot instruction fFBSCLK =%f Mhz, fFBSCLK timing violation at %f \n", fFBSCLK4, $realtime );

        T_SCLK_P = $realtime; 
        #0;  
        //tDVCH
        if ( T_SCLK_P - T_SI < tDVCH && SI_IN_EN && T_SCLK_P > 0 )
            $fwrite (AC_Check_File, "minimum Data SI setup time tDVCH=%f ns, tDVCH timing violation at %f \n", tDVCH, $realtime );
        if ( T_SCLK_P - T_SO < tDVCH && SO_IN_EN && T_SCLK_P > 0 )
            $fwrite (AC_Check_File, "minimum Data SO setup time tDVCH=%f ns, tDVCH timing violation at %f \n", tDVCH, $realtime );
        if ( T_SCLK_P - T_WP < tDVCH && WP_IN_EN && T_SCLK_P > 0 )
            $fwrite (AC_Check_File, "minimum Data WP setup time tDVCH=%f ns, tDVCH timing violation at %f \n", tDVCH, $realtime );

        if ( T_SCLK_P - T_SIO3 < tDVCH && SIO3_IN_EN && T_SCLK_P > 0 )
            $fwrite (AC_Check_File, "minimum Data SIO3 setup time tDVCH=%f ns, tDVCH timing violation at %f \n", tDVCH, $realtime );
        //tCL
        if ( T_SCLK_P - T_SCLK_N < tCL && ~CS && T_SCLK_P > 0 )
            $fwrite (AC_Check_File, "minimum SCLK Low time tCL=%f ns, tCL timing violation at %f \n", tCL, $realtime );
        //tCL_R
        if ( T_SCLK_P - T_SCLK_N < tCL_R && Read_1XIO_Chk && T_SCLK_P > 0 )
            $fwrite (AC_Check_File, "minimum SCLK Low time tCL=%f ns, tCL timing violation at %f \n", tCL_R, $realtime );
       //tCL_4PP
        if ( T_SCLK_P - T_SCLK_N < tCL_4PP && PP_4XIO_Chk && T_SCLK_P > 0 )
            $fwrite (AC_Check_File, "minimum SCLK Low time tCL=%f ns, tCL timing violation at %f \n", tCL_4PP, $realtime );
        #0;
        // tSLCH
        if ( T_SCLK_P - T_CS_N < tSLCH  && T_SCLK_P > 0 )
            $fwrite (AC_Check_File, "minimum CS# active setup time tSLCH=%f ns, tSLCH timing violation at %f \n", tSLCH, $realtime );

        // tSHCH
        if ( T_SCLK_P - T_CS_P < tSHCH  && T_SCLK_P > 0 )
            $fwrite (AC_Check_File, "minimum CS# not active setup time tSHCH=%f ns, tSHCH timing violation at %f \n", tSHCH, $realtime );
    end

    always @ ( negedge SCLK ) begin
        T_SCLK_N = $realtime;
        #0; 
        //tCH
        if ( T_SCLK_N - T_SCLK_P < tCH && ~CS && T_SCLK_N > 0 )
            $fwrite (AC_Check_File, "minimum SCLK High time tCH=%f ns, tCH timing violation at %f \n", tCH, $realtime );
        //tCH_R
        if ( T_SCLK_N - T_SCLK_P < tCH_R && Read_1XIO_Chk && T_SCLK_N > 0 )
            $fwrite (AC_Check_File, "minimum SCLK High time tCH=%f ns, tCH timing violation at %f \n", tCH_R, $realtime );
       //tCH_4PP
        if ( T_SCLK_N - T_SCLK_P < tCH_4PP && PP_4XIO_Chk && T_SCLK_N > 0 )
            $fwrite (AC_Check_File, "minimum SCLK High time tCH=%f ns, tCH timing violation at %f \n", tCH_4PP, $realtime );
    end


    always @ ( SI ) begin
        T_SI = $realtime; 
        #0;  
        //tCHDX
        if ( T_SI - T_SCLK_P < tCHDX && SI_IN_EN && T_SI > 0 )
            $fwrite (AC_Check_File, "minimum Data SI hold time tCHDX=%f ns, tCHDX timing violation at %f \n", tCHDX, $realtime );
    end

    always @ ( SO ) begin
        T_SO = $realtime; 
        #0;  
        //tCHDX
        if ( T_SO - T_SCLK_P < tCHDX && SO_IN_EN && T_SO > 0 )
            $fwrite (AC_Check_File, "minimum Data SO hold time tCHDX=%f ns, tCHDX timing violation at %f \n", tCHDX, $realtime );
    end

    always @ ( WP ) begin
        T_WP = $realtime; 
        #0;  
        //tCHDX
        if ( T_WP - T_SCLK_P < tCHDX && WP_IN_EN && T_WP > 0 )
            $fwrite (AC_Check_File, "minimum Data WP hold time tCHDX=%f ns, tCHDX timing violation at %f \n", tCHDX, $realtime );
    end

    always @ ( SIO3 ) begin
        T_SIO3 = $realtime; 
        #0;  
        //tCHDX
       if ( T_SIO3 - T_SCLK_P < tCHDX && SIO3_IN_EN && T_SIO3 > 0 )
            $fwrite (AC_Check_File, "minimum Data SIO3 hold time tCHDX=%f ns, tCHDX timing violation at %f \n", tCHDX, $realtime );
    end

    always @ ( posedge CS ) begin
        T_CS_P = $realtime;
        #0;  
        // tCHSH 
        if ( T_CS_P - T_SCLK_P < tCHSH  && T_CS_P > 0 )
            $fwrite (AC_Check_File, "minimum CS# active hold time tCHSH=%f ns, tCHSH timing violation at %f \n", tCHSH, $realtime );
       // tRH
       if ( T_CS_P - T_RESET_N < tRH  && T_CS_P > 0 )
            $fwrite (AC_Check_File, "minimum hold time tRH=%f ns, tRH timing violation at %f \n", tRH, $realtime );
    end

    always @ ( negedge CS ) begin
        T_CS_N = $realtime;
        #0;
        //tCHSL
        if ( T_CS_N - T_SCLK_P < tCHSL  && T_CS_N > 0 )
            $fwrite (AC_Check_File, "minimum CS# not active hold time tCHSL=%f ns, tCHSL timing violation at %f \n", tCHSL, $realtime );
        //tSHSL
        if ( T_CS_N - T_CS_P < tSHSL_R && T_CS_N > 0 && Read_SHSL)
            $fwrite (AC_Check_File, "minimum CS# deselect  time tSHSL_R=%f ns, tSHSL timing violation at %f \n", tSHSL_R, $realtime );
        if ( T_CS_N - T_CS_P < tSHSL_W && T_CS_N > 0 && Write_SHSL)
            $fwrite (AC_Check_File, "minimum CS# deselect  time tSHSL_W=%f ns, tSHSL timing violation at %f \n", tSHSL_W, $realtime );

        //tWHSL
        if ( T_CS_N - T_WP_P < tWHSL && WP_EN  && T_CS_N > 0 )
            $fwrite (AC_Check_File, "minimum WP setup  time tWHSL=%f ns, tWHSL timing violation at %f \n", tWHSL, $realtime );


        //tDP
        if ( T_CS_N - T_CS_P < tDP && T_CS_N > 0 && tDP_Chk)
            $fwrite (AC_Check_File, "when transit from Standby Mode to Deep-Power Mode, CS# must remain high for at least tDP =%f ns, tDP timing violation at %f \n", tDP, $realtime );


        //tRES1/2
        if ( T_CS_N - T_CS_P < tRES1 && T_CS_N > 0 && tRES1_Chk)
            $fwrite (AC_Check_File, "when transit from Deep-Power Mode to Standby Mode, CS# must remain high for at least tRES1 =%f ns, tRES1 timing violation at %f \n", tRES1, $realtime );

        if ( T_CS_N - T_CS_P < tRES2 && T_CS_N > 0 && tRES2_Chk)
            $fwrite (AC_Check_File, "when transit from Deep-Power Mode to Standby Mode, CS# must remain high for at least tRES2 =%f ns, tRES2 timing violation at %f \n", tRES2, $realtime );

        //tRHSL
        if ( T_CS_N - T_RESET_P < tRHSL && T_CS_N > 0 )
            $fwrite (AC_Check_File, "minimum Reset# high before CS# low time tRHSL=%f ns, tRHSL timing violation at %f \n", tRHSL, $realtime );
    end

    always @ ( posedge WP ) begin
        T_WP_P = $realtime;
        #0;  
    end

    always @ ( negedge WP ) begin
        T_WP_N = $realtime;
        #0;
        //tSHWL
        if ( ((T_WP_N - T_CS_P < tSHWL) || ~CS) && WP_EN && T_WP_N > 0 )
            $fwrite (AC_Check_File, "minimum WP hold time tSHWL=%f ns, tSHWL timing violation at %f \n", tSHWL, $realtime );
    end

    always @ ( negedge RESETB_INT ) begin
        T_RESET_N = $realtime;
        #0;
        //tRS
        if ( (T_RESET_N - T_CS_P < tRS) && T_RESET_N > 0 )
            $fwrite (AC_Check_File, "minimum setup time tRS=%f ns, tRS timing violation at %f \n", tRS, $realtime );
    end

    always @ ( posedge RESETB_INT ) begin
        T_RESET_P = $realtime;
        #0;
        //tRLRH
        if ( (T_RESET_P - T_RESET_N < tRLRH) && T_RESET_P > 0 )
            $fwrite (AC_Check_File, "minimum reset pulse width tRLRH=%f ns, tRLRH timing violation at %f \n", tRLRH, $realtime );
    end
endmodule

