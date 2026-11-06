"""Minimalus pygame 'stub' - leidžia paleisti logikos smoke testą be pygame įdiegimo."""
import sys
import types

class Rect:
    def __init__(self, *a):
        if len(a) == 1:
            a = tuple(a[0])
        if len(a) == 2:
            (x, y), (w, h) = a
        else:
            x, y, w, h = a
        object.__setattr__(self, "x", int(x)); object.__setattr__(self, "y", int(y))
        object.__setattr__(self, "w", int(w)); object.__setattr__(self, "h", int(h))
    width = property(lambda s: s.w); height = property(lambda s: s.h)
    left = property(lambda s: s.x); top = property(lambda s: s.y)
    right = property(lambda s: s.x + s.w); bottom = property(lambda s: s.y + s.h)
    centerx = property(lambda s: s.x + s.w // 2); centery = property(lambda s: s.y + s.h // 2)
    center = property(lambda s: (s.x + s.w // 2, s.y + s.h // 2))
    topleft = property(lambda s: (s.x, s.y))
    def __setattr__(self, k, v):
        w, h = self.w, self.h
        m = {"center": lambda: (v[0] - w // 2, v[1] - h // 2), "midleft": lambda: (v[0], v[1] - h // 2),
             "midright": lambda: (v[0] - w, v[1] - h // 2), "topleft": lambda: v,
             "midtop": lambda: (v[0] - w // 2, v[1]), "topright": lambda: (v[0] - w, v[1]),
             "midbottom": lambda: (v[0] - w // 2, v[1] - h), "bottomleft": lambda: (v[0], v[1] - h),
             "bottomright": lambda: (v[0] - w, v[1] - h)}
        if k in m:
            x, y = m[k](); object.__setattr__(self, "x", int(x)); object.__setattr__(self, "y", int(y))
        else:
            object.__setattr__(self, k, v)
    def colliderect(self, o):
        return self.x < o.x + o.w and o.x < self.x + self.w and self.y < o.y + o.h and o.y < self.y + self.h
    def collidepoint(self, p):
        return self.x <= p[0] < self.x + self.w and self.y <= p[1] < self.y + self.h
    def inflate(self, dx, dy):
        return Rect(self.x - dx // 2, self.y - dy // 2, self.w + dx, self.h + dy)
    def inflate_ip(self, dx, dy):
        object.__setattr__(self, "x", self.x - dx // 2); object.__setattr__(self, "y", self.y - dy // 2)
        object.__setattr__(self, "w", self.w + dx); object.__setattr__(self, "h", self.h + dy)
    def move(self, dx, dy): return Rect(self.x + dx, self.y + dy, self.w, self.h)
    def copy(self): return Rect(self.x, self.y, self.w, self.h)

class Surface:
    def __init__(self, size=(1, 1), flags=0):
        self.size = (int(size[0]), int(size[1]))
    def get_width(self): return self.size[0]
    def get_height(self): return self.size[1]
    def get_size(self): return self.size
    def get_rect(self, **kw):
        r = Rect(0, 0, *self.size)
        for k, v in kw.items(): setattr(r, k, v)
        return r
    def blit(self, *a, **k): return Rect(0, 0, 1, 1)
    def fill(self, *a, **k): pass
    def copy(self): return Surface(self.size)
    def convert(self): return self
    def convert_alpha(self): return self
    def set_alpha(self, *a): pass
    def set_at(self, *a): pass

def _noop(*a, **k): return Rect(0, 0, 1, 1)

class Font:
    def render(self, text, aa, color): return Surface((max(1, len(text) * 12), 28))
    def set_bold(self, b): pass

class Sound:
    created = 0
    def __init__(self, buffer=None):
        Sound.created += 1; self.nbytes = len(buffer) if buffer else 0
    def set_volume(self, v): pass
    def play(self, *a, **k): pass

class Channel:
    def __init__(self, i): pass
    def play(self, *a, **k): pass
    def stop(self): pass
    def set_volume(self, v): pass

class Clock:
    def tick(self, f): return 16

class Keys:
    def __init__(self, down=()): self.down = set(down)
    def __getitem__(self, k): return k in self.down

def build():
    m = types.ModuleType("pygame")
    m.Rect, m.Surface = Rect, Surface
    for i, n in enumerate("QUIT KEYDOWN MOUSEMOTION MOUSEBUTTONDOWN SRCALPHA SCALED BLEND_RGB_ADD BLEND_RGB_SUB JOYAXISMOTION JOYHATMOTION JOYBUTTONDOWN JOYDEVICEADDED JOYDEVICEREMOVED FINGERDOWN FINGERMOTION FINGERUP MOUSEBUTTONUP FULLSCREEN APP_WILLENTERBACKGROUND APP_DIDENTERBACKGROUND".split()):
        setattr(m, n, 1000 + i)
    for i, n in enumerate("K_LEFT K_RIGHT K_UP K_DOWN K_a K_d K_w K_s K_SPACE K_p K_ESCAPE K_RETURN K_KP_ENTER K_q K_m K_b K_x K_LCTRL K_F11 K_BACKSPACE K_TAB K_AC_BACK".split()):
        setattr(m, n, 100 + i)
    m.draw = types.SimpleNamespace(**{n: _noop for n in "circle ellipse polygon line lines rect arc".split()})
    m.transform = types.SimpleNamespace(
        rotozoom=lambda s, a, sc: Surface((s.size[0] * sc, s.size[1] * sc)),
        rotate=lambda s, a: Surface(s.size), smoothscale=lambda s, sz: Surface(sz),
        scale=lambda s, sz: Surface(sz))
    m.font = types.SimpleNamespace(SysFont=lambda *a, **k: Font())
    state = {"mixer": (44100, -16, 2)}
    m.mixer = types.SimpleNamespace(
        pre_init=lambda *a: None, init=lambda *a: None, get_init=lambda: state["mixer"],
        set_num_channels=lambda n: None, set_reserved=lambda n: None, Sound=Sound, Channel=Channel,
        music=types.SimpleNamespace(stop=lambda: None, load=lambda p: None, play=lambda *a, **k: None,
                                    set_volume=lambda v: None))
    m.display = types.SimpleNamespace(set_mode=lambda *a, **k: Surface((800, 700)), set_caption=lambda s: None,
                                      flip=lambda: None, toggle_fullscreen=lambda: None,
                                      get_window_size=lambda: (1600, 720))
    m.time = types.SimpleNamespace(Clock=Clock)
    m.event = types.SimpleNamespace(get=lambda: [], pump=lambda: None)
    m.key = types.SimpleNamespace(get_pressed=lambda: Keys())
    m.joystick = types.SimpleNamespace(init=lambda: None, get_count=lambda: 0)
    m.init = lambda: None
    m.quit = lambda: None
    m.Keys = Keys
    sys.modules["pygame"] = m
    return m
