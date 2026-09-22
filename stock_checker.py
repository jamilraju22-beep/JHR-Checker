"""Fast, classic-CV Adobe Stock technical pre-checks."""
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
import cv2
import numpy as np

MIN_MEGAPIXELS, MAX_MEGAPIXELS, MAX_FILE_SIZE_MB = 3.83, 100.0, 45.0
BLUR_FAIL_THRESHOLD, BLUR_WARN_THRESHOLD = 60.0, 120.0
NOISE_WARN_THRESHOLD, NOISE_FAIL_THRESHOLD = 6.0, 12.0
CLIP_WARN_PCT, CLIP_FAIL_PCT = 1.0, 4.0
CONTRAST_LOW_WARN, CONTRAST_HIGH_WARN = 30.0, 85.0
SATURATION_LOW_WARN, SATURATION_HIGH_WARN = 15.0, 200.0
CA_WARN_THRESHOLD, CA_FAIL_THRESHOLD = 3.0, 6.0
HORIZON_TILT_WARN_DEG, HORIZON_TILT_FAIL_DEG = 1.5, 4.0

@dataclass
class CheckResult:
    name: str; status: str; message: str; value: Optional[float] = None; auto_fixable: bool = False

@dataclass
class Report:
    file: str; width: int; height: int; megapixels: float; file_size_mb: float
    checks: list = field(default_factory=list)
    @property
    def overall(self):
        statuses = [c.status for c in self.checks]
        return "fail" if "fail" in statuses else "warn" if "warn" in statuses else "pass"
    def to_dict(self):
        d = asdict(self); d["overall"] = self.overall; return d

def result(name, status, message, value=None, fix=False):
    return CheckResult(name, status, message, value, fix)

def check_resolution(img):
    h,w=img.shape[:2]; mp=w*h/1e6
    if mp<MIN_MEGAPIXELS: return result("resolution","fail",f"{w}×{h} ({mp:.1f}MP) is below the 3.83MP minimum. Do not upscale.",mp)
    if mp>MAX_MEGAPIXELS: return result("resolution","fail",f"{w}×{h} ({mp:.1f}MP) exceeds the 100MP ceiling.",mp,True)
    return result("resolution","pass",f"{w}×{h} ({mp:.1f}MP) is within range.",mp)

def check_file_size(mb):
    return result("file_size","fail" if mb>45 else "pass",f"{mb:.1f}MB {'exceeds' if mb>45 else 'is within'} Adobe's 45MB cap.",mb,mb>45)

def check_blur(gray):
    v=float(cv2.Laplacian(gray,cv2.CV_64F).var()); s="fail" if v<60 else "warn" if v<120 else "pass"
    msg={"fail":"Very low edge sharpness; image is likely soft or out of focus.","warn":"Borderline sharpness; inspect at 100%.","pass":"Sharpness looks good."}[s]
    return result("focus_blur",s,f"{msg} (Laplacian variance {v:.1f}).",v,s!="fail")

def check_noise(gray):
    sigma=float(np.std(gray.astype(np.float32)-cv2.medianBlur(gray,5))); s="fail" if sigma>12 else "warn" if sigma>6 else "pass"
    return result("noise",s,f"Noise estimate: sigma {sigma:.1f}.",sigma,s!="pass")

def check_exposure(gray):
    black=float(np.mean(gray<=2)*100); white=float(np.mean(gray>=253)*100); worst=max(black,white); which="shadows" if black>white else "highlights"; s="fail" if worst>4 else "warn" if worst>1 else "pass"
    return result("exposure",s,f"{worst:.1f}% of pixels clipped in the {which}." if s!="pass" else "Exposure looks well balanced.",worst,s!="pass")

def check_contrast(gray):
    v=float(np.std(gray)); s="warn" if v<30 or v>85 else "pass"; msg="Low contrast — image may look flat." if v<30 else "Very high contrast — check crushed tones." if v>85 else "Contrast looks reasonable."
    return result("contrast",s,f"{msg} (std dev {v:.1f}).",v,s=="warn")

def check_saturation(bgr):
    v=float(np.mean(cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)[:,:,1])); s="warn" if v<15 or v>200 else "pass"; msg="Colors may look washed out." if v<15 else "May look unnaturally oversaturated." if v>200 else "Saturation looks natural."
    return result("saturation",s,f"{msg} ({v:.0f}/255).",v,s=="warn")

def check_white_balance(bgr):
    b,g,r=cv2.mean(bgr)[:3]; avg=(b+g+r)/3; v=max(abs(b-avg),abs(g-avg),abs(r-avg))/(avg+1e-6)*100; s="warn" if v>25 else "pass"; cast="warm" if r>b else "cool"
    return result("white_balance",s,f"Possible {cast} color cast ({v:.0f}% channel deviation)." if s=="warn" else "White balance looks neutral.",v,s=="warn")

def check_chromatic_aberration(bgr):
    b,_,r=cv2.split(bgr); er=cv2.Canny(r,100,200); eb=cv2.Canny(b,100,200); h,w=er.shape; a=er[:max(1,h//10),:]; c=eb[:max(1,h//10),:]
    if not a.sum() or not c.sum(): return result("chromatic_aberration","pass","No strong edges to evaluate.",0)
    scores=[(np.sum(a & np.roll(c,dx,axis=1)),abs(dx)) for dx in range(-6,7)]; off=max(scores)[1]; s="fail" if off>=6 else "warn" if off>=3 else "pass"
    return result("chromatic_aberration",s,f"Possible color fringing (edge offset ~{off}px)." if s!="pass" else "No significant fringing detected.",float(off),s!="pass")

def check_horizon_tilt(gray):
    lines=cv2.HoughLines(cv2.Canny(gray,50,150),1,np.pi/180,150); angles=[] if lines is None else [(x[0][1]*180/np.pi)-90 for x in lines[:50] if -45<((x[0][1]*180/np.pi)-90)<45]
    tilt=abs(float(np.median(angles))) if angles else 0; s="fail" if tilt>=4 else "warn" if tilt>=1.5 else "pass"
    return result("composition_tilt",s,f"Dominant lines suggest ~{tilt:.1f}° tilt." if s!="pass" else "No significant tilt detected.",tilt,s!="pass")

def run_checks(image_path):
    bgr=cv2.imread(image_path,cv2.IMREAD_COLOR)
    if bgr is None: raise ValueError(f"Could not read image: {image_path}")
    gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY); h,w=bgr.shape[:2]; mb=os.path.getsize(image_path)/(1024*1024)
    checks=[check_resolution(bgr),check_file_size(mb),check_blur(gray),check_noise(gray),check_exposure(gray),check_contrast(gray),check_saturation(bgr),check_white_balance(bgr),check_chromatic_aberration(bgr),check_horizon_tilt(gray)]
    return Report(image_path,w,h,round(w*h/1e6,2),round(mb,2),checks)
