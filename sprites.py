"""Image helpers shared by main.py and combat_proto.py.

Everything here works on lists of frames (Surfaces), like the image
sequences from class 11.
"""
import pygame


def load_image_safely(path):
    """Load a PNG with transparency, or return None if it is missing."""
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None


def cut_frames(sheet, rects):
    """Cut frames out of a spritesheet, one (x, y, w, h) rectangle per frame (class 11)."""
    return [sheet.subsurface(pygame.Rect(r)).copy() for r in rects]


def clean_frame(frame):
    """Remove bits of NEIGHBOURING frames that poke into this frame's rectangle.

    Uses masks (class 11). The frame is split into separate blobs of opaque
    pixels. We keep the biggest blob (the creature) and any blob that floats
    freely inside the rectangle (sparks, loose leaves). A blob that touches the
    rectangle's edge but isn't the biggest is a piece of the next frame over.
    """
    mask = pygame.mask.from_surface(frame)
    blobs = mask.connected_components()
    if not blobs:
        return frame
    biggest = max(blobs, key=lambda blob: blob.count())
    edge = frame.get_rect()
    keep = pygame.mask.Mask(frame.get_size())
    for blob in blobs:
        box = blob.get_bounding_rects()[0]
        touches_edge = (box.left == 0 or box.top == 0 or
                        box.right == edge.right or box.bottom == edge.bottom)
        if blob is biggest or not touches_edge:
            keep.draw(blob, (0, 0))
    return keep.to_surface(setsurface=frame, unsetcolor=(0, 0, 0, 0))


def crop_to_content(frames):
    """Trim the empty transparent border, using ONE box for every frame so nothing jitters."""
    box = frames[0].get_bounding_rect()
    for frame in frames[1:]:
        box.union_ip(frame.get_bounding_rect())
    if box.width == 0 or box.height == 0:
        return frames
    return [frame.subsurface(box).copy() for frame in frames]


def feet_position(frame):
    """(x, y) of the middle of the character's feet inside a frame.

    Uses the bottom strip of visible pixels, so antlers or a raised arm
    don't pull the anchor sideways the way the image center would.
    """
    body = frame.get_bounding_rect()
    strip_h = max(1, body.height // 12)
    feet = frame.subsurface((0, body.bottom - strip_h, frame.get_width(), strip_h)).get_bounding_rect()
    return feet.centerx, body.bottom


def align_by_feet(frames):
    """Put every frame on a same-size canvas with the feet at the bottom-center.

    After this, get_rect(midbottom=...) places the FEET exactly on the spot,
    for every frame, so the animation doesn't slide or hop.
    """
    anchors = [feet_position(f) for f in frames]
    half = max(max(fx, f.get_width() - fx) for f, (fx, _) in zip(frames, anchors))
    height = max(bottom for _, bottom in anchors)
    aligned = []
    for f, (fx, bottom) in zip(frames, anchors):
        canvas = pygame.Surface((half * 2, height), pygame.SRCALPHA)
        canvas.blit(f, (half - fx, height - bottom))
        aligned.append(canvas)
    return aligned


def scale_frames(frames, factor, smooth=False):
    """scale keeps pixel art crisp; smoothscale looks better when SHRINKING painted art."""
    scale = pygame.transform.smoothscale if smooth else pygame.transform.scale
    return [scale(f, (max(1, round(f.get_width() * factor)), max(1, round(f.get_height() * factor))))
            for f in frames]


def flip_frames(frames):
    return [pygame.transform.flip(f, True, False) for f in frames]


def outlined(frames, color, thickness=2):
    """Add a soft colored outline around each frame (class 11: masks).

    A mask of the opaque pixels becomes a one-color silhouette, drawn 8 times
    around the sprite before the sprite itself.
    """
    result = []
    for frame in frames:
        silhouette = pygame.mask.from_surface(frame).to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
        canvas = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
        t = thickness
        for dx, dy in ((-t, 0), (t, 0), (0, -t), (0, t), (-t, -t), (t, t), (-t, t), (t, -t)):
            canvas.blit(silhouette, (dx, dy))
        canvas.blit(frame, (0, 0))
        result.append(canvas)
    return result


def tinted(frames, color, flag):
    """Copies of the frames with a color added or multiplied (e.g. frost)."""
    result = []
    for frame in frames:
        copy = frame.copy()
        copy.fill(color, special_flags=flag)
        result.append(copy)
    return result


def body_rect(frame, feet):
    """Screen rectangle around the visible pixels of a frame standing at feet."""
    placed = frame.get_rect(midbottom=feet)
    return frame.get_bounding_rect().move(placed.topleft)
