# Tested and confirmed to work with Schneider Electric Pro-face XVGU3SHAG
# and XVGU3SWG signal towers.

# This project is an independent implementation
# and not affiliated with Schneider Electric.

import sys, time, argparse
import usb.core, usb.util

VID, PID = 0x16DE, 0x000C

# ----- Enum/Consts -----
LED_LYE = {'ONE': 0, 'TWO': 1, 'THREE': 2}
LED     = {'OFF': 0, 'ON': 1, 'DUTY': 2}
LED_PTN = {'OFF': 0, 'ON': 1, 'BLINK_1': 2, 'BLINK_2': 3}
BZR_TON = {'HI': 0, 'LOW': 1}
BZR_VOL = {'BIG': 0, 'MID': 1, 'SML': 2}
BZR_PTN = {'OFF': 0, 'PTN_1': 1, 'PTN_2': 2, 'PTN_3': 3, 'PTN_4': 4}
SRD_KND = {'LED_01': 0, 'LED_02': 1, 'LED_03': 2, 'BUZZER': 3}

CNF_KND1 = {'LED':0,'BUZ':1,'ALLDEF':2}
CNF_KND2_LED = {'RLED':0,'GLED':1,'BLED':2}

COLOR_TABLE = {
    "off": (0,0,0), "white": (255,255,255),
    "red": (255,0,0), "yellow": (255,255,0), "blue": (0,0,255),
    "pink": (255,192,203), "light_pink":(255,182,193),
    "deep_pink":(255,20,147), "hot_pink":(255,105,180),
    "rose":(255,0,127), "salmon":(250,128,114),
    "plum":(221,160,221), "orchid":(218,112,214),
    "pale_violet":(219,112,147), "misty_rose":(255,228,225),
}

CMD_LED_SGLSET = 0x01
CMD_BZR_SGLSET = 0x02
CMD_STS_READ   = 0x03
CMD_PTN_SET    = 0x04
CMD_PTN_READ   = 0x05
CMD_PTN_DO     = 0x06
CMD_CONF_SET   = 0x07
CMD_CONF_READ  = 0x08

def _len_be(n:int): return bytes(((n>>8)&0xFF, n&0xFF))
def _checksum(data:bytes): return sum(data)&0xFF

def build_led_packet(layer,r,g,b,ptn):
    pkt=bytearray(11)
    pkt[0]=0x1B; pkt[1]=CMD_LED_SGLSET
    pkt[2],pkt[3]=_len_be(5)
    pkt[4]=layer; pkt[5]=r; pkt[6]=g; pkt[7]=b; pkt[8]=ptn
    pkt[9]=_checksum(bytes(pkt[1:9])); pkt[10]=0x0D
    return bytes(pkt)

def build_buzzer_packet(tone,vol,ptn):
    pkt=bytearray(9)
    pkt[0]=0x1B; pkt[1]=CMD_BZR_SGLSET
    pkt[2],pkt[3]=_len_be(3)
    pkt[4]=tone; pkt[5]=vol; pkt[6]=ptn
    pkt[7]=_checksum(bytes(pkt[1:7])); pkt[8]=0x0D
    return bytes(pkt)

def build_read_packet(kind):
    pkt=bytearray(7)
    pkt[0]=0x1B; pkt[1]=CMD_STS_READ
    pkt[2],pkt[3]=_len_be(1)
    pkt[4]=kind; pkt[5]=_checksum(bytes(pkt[1:5])); pkt[6]=0x0D
    return bytes(pkt)

def build_conf_set_packet(kind1,kind2,param):
    pkt=bytearray(9)
    pkt[0]=0x1B; pkt[1]=CMD_CONF_SET
    pkt[2],pkt[3]=_len_be(3)
    pkt[4]=kind1; pkt[5]=kind2; pkt[6]=param
    pkt[7]=_checksum(bytes(pkt[1:7])); pkt[8]=0x0D
    return bytes(pkt)

def build_conf_read_packet(kind1,kind2):
    pkt=bytearray(8)
    pkt[0]=0x1B; pkt[1]=CMD_CONF_READ
    pkt[2],pkt[3]=_len_be(2)
    pkt[4]=kind1; pkt[5]=kind2
    pkt[6]=_checksum(bytes(pkt[1:6])); pkt[7]=0x0D
    return bytes(pkt)

def build_ptn_do_packet(ptn_no,run_flag):
    pkt=bytearray(8)
    pkt[0]=0x1B; pkt[1]=CMD_PTN_DO
    pkt[2],pkt[3]=_len_be(2)
    pkt[4]=ptn_no; pkt[5]=run_flag
    pkt[6]=_checksum(bytes(pkt[1:6])); pkt[7]=0x0D
    return bytes(pkt)

def open_dev():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        raise RuntimeError("XVGU not found")

    cfg = dev.get_active_configuration()
    intf = usb.util.find_descriptor(cfg, bInterfaceNumber=1, bAlternateSetting=0)
    if intf is None:
        raise RuntimeError("Interface1 not found")

    dev.set_configuration()

    ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT and usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK)
    ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN and usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK)

    return dev, ep_out, ep_in

def send_packet(ep_out,pkt,timeout=1000): ep_out.write(pkt,timeout)

def _rgb_chan_to_led(v):
    if v<=0: return LED['OFF']
    if v>=170: return LED['ON']
    return LED['DUTY']

def set_led(ep_out,layer,color,pattern="ON"):
    layer_raw=LED_LYE[layer.upper()] if isinstance(layer,str) else int(layer)
    if isinstance(color,str): rgb=COLOR_TABLE[color.lower()]
    else: r,g,b=color; rgb=(int(r),int(g),int(b))
    pkt=build_led_packet(layer_raw,_rgb_chan_to_led(rgb[0]),_rgb_chan_to_led(rgb[1]),_rgb_chan_to_led(rgb[2]),LED_PTN[pattern.upper()])
    send_packet(ep_out,pkt)

def buzz_for(ep_out, tone="HI", volume="MID", pattern="PTN_2"):
    send_packet(ep_out, build_buzzer_packet(BZR_TON[tone], BZR_VOL[volume], BZR_PTN[pattern]))

def buzz_off(ep_out):
    send_packet(ep_out, build_buzzer_packet(BZR_TON['LOW'], BZR_VOL['SML'], BZR_PTN['OFF']))

def _canon_tone(val):
    """Map user input to protocol tone keys."""
    if not val:
        return "HI"
    v = str(val).strip().lower()
    return "LOW" if v.startswith("low") else "HI"  # default high

def read_status(ep_out,ep_in,kind):
    pkt=build_read_packet(SRD_KND[kind]); send_packet(ep_out,pkt)
    return bytes(ep_in.read(64,timeout=1000))

def _release_dev(dev):
    if not dev:
        return
    try:
        usb.util.release_interface(dev, 1)
    except Exception:
        pass
    try:
        usb.util.dispose_resources(dev)
    except Exception:
        pass

def main():
    p=argparse.ArgumentParser(description="Schneider XVGU control")
    sub=p.add_subparsers(dest="cmd")

    pc=sub.add_parser("ledset")
    pc.add_argument("--layer",required=True)
    g=pc.add_mutually_exclusive_group(required=True)
    g.add_argument("--name")
    g.add_argument("--rgb")
    pc.add_argument("--pattern",default="ON")

    pb=sub.add_parser("buzzer")
    pb.add_argument("--seconds",type=float)
    pb.add_argument("--tone", choices=["low", "high"])
    pb.add_argument("--volume", choices=["big", "mid", "sml"], default="mid")
    pb.add_argument("--off", action="store_true", help="Stop buzzer")

    pr=sub.add_parser("read")
    pr.add_argument("kind",choices=list(SRD_KND.keys()))

    pcfg=sub.add_parser("confset")
    pcfg.add_argument("kind1",type=int)
    pcfg.add_argument("kind2",type=int)
    pcfg.add_argument("param",type=int)

    pcfr=sub.add_parser("confread")
    pcfr.add_argument("kind1",type=int)
    pcfr.add_argument("kind2",type=int)

    ptd=sub.add_parser("ptndo")
    ptd.add_argument("ptn_no",type=int)
    ptd.add_argument("run_flag",type=int)

    args=p.parse_args()
    if not args.cmd:
        print("XVGU Signal Tower Controller (Unofficial)")
        print("Usage: python xvgu.py <command> [options]\n")
        print("Available commands:")
        print("  ledset   Control LED lights")
        print("  buzzer   Control buzzer\n")
        print("Run 'python xvgu.py <command> -h' for details on each command.")
        return

    dev,ep_out,ep_in=open_dev()

    if args.cmd=="ledset":
        color=args.name if args.name else tuple(int(x) for x in args.rgb.split(","))
        set_led(ep_out,args.layer,color,args.pattern)
        print("OK")

    elif args.cmd == "buzzer":
        try:
            if args.off:
                buzz_off(ep_out)
                print("OK buzzer OFF")
            else:
                tone = _canon_tone(args.tone)
                volume = args.volume.upper()
                buzz_for(ep_out, tone=tone, volume=volume)
                print(f"OK buzzer ON (tone={tone}, volume={volume})")
                if args.seconds and args.seconds > 0:
                    _release_dev(dev)
                    dev = None; ep_out = None; ep_in = None

                    time.sleep(args.seconds)

                    dev,ep_out,ep_in = open_dev()
                    buzz_off(ep_out)
                    print("OK buzzer OFF")
        finally:
            _release_dev(dev)

    elif args.cmd=="read":
        print("RAW:",read_status(ep_out,ep_in,args.kind).hex())

    elif args.cmd=="confset":
        send_packet(ep_out,build_conf_set_packet(args.kind1,args.kind2,args.param))
        print("OK confset")

    elif args.cmd=="confread":
        pkt=build_conf_read_packet(args.kind1,args.kind2)
        send_packet(ep_out,pkt)
        raw=bytes(ep_in.read(64,timeout=1000))
        print("RAW:",raw.hex())

    elif args.cmd=="ptndo":
        send_packet(ep_out,build_ptn_do_packet(args.ptn_no,args.run_flag))
        print("OK ptndo")

if __name__=="__main__":
    main()
