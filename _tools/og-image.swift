// Renders the social preview (assets/og-image.png) from the page's own
// geometry, scaled up: the leaning column, the tilted gold card and its
// hairline, Roux breaking the bottom edge, and the chip row. If the tilts,
// offsets or colours in index.html change, change them here too.
//
// From the repo root:
//   swift _tools/og-image.swift art-source/gravyrobot-roux-sketch.png assets/og-image.png
// (If swift complains the SDK doesn't match the compiler, prefix it with
// SDKROOT=$(xcrun --show-sdk-path --sdk macosx26.5) or another older SDK.)
//
// The underscore keeps Jekyll from publishing this folder.
import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let input = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2])
let W = 1200.0, H = 630.0
let s = 800.0 / 620.0                       // page card is 620 wide; here 800

func rgb(_ hex: UInt32) -> CGColor {
  CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255,
          blue: CGFloat(hex & 255) / 255, alpha: 1)
}
let gold = rgb(0xF4C21B), line = rgb(0xE7E1D0), bg = rgb(0xFDFCF7)
let chipColors: [UInt32] = [0xF4C21B, 0x1C6B4E, 0xE93B7A, 0x8E2B22, 0x181613, 0x5a5650, 0xE7E1D0]
let rad = { (d: Double) in d * .pi / 180 }

let ctx = CGContext(data: nil, width: Int(W), height: Int(H), bitsPerComponent: 8, bytesPerRow: 0,
                    space: CGColorSpace(name: CGColorSpace.sRGB)!,
                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.interpolationQuality = .high
ctx.translateBy(x: 0, y: H); ctx.scaleBy(x: 1, y: -1)   // y-down, like CSS; positive angles turn clockwise

// Fill a rounded rect of size w×h centred on (cx, cy), turned by deg.
func box(_ cx: Double, _ cy: Double, _ w: Double, _ h: Double, _ r: Double, _ deg: Double,
         fill: CGColor? = nil, stroke: CGColor? = nil, width: Double = 0) {
  ctx.saveGState()
  ctx.translateBy(x: cx, y: cy); ctx.rotate(by: rad(deg))
  // A CSS border sits inside the box, so inset the stroke by half its width.
  let i = width / 2
  let rect = CGRect(x: -w / 2 + i, y: -h / 2 + i, width: w - 2 * i, height: h - 2 * i)
  let path = CGPath(roundedRect: rect, cornerWidth: max(r - i, 0), cornerHeight: max(r - i, 0), transform: nil)
  ctx.addPath(path)
  if let fill { ctx.setFillColor(fill); ctx.fillPath() }
  if let stroke { ctx.setStrokeColor(stroke); ctx.setLineWidth(width); ctx.strokePath() }
  ctx.restoreGState()
}

// Page: beige ground, cream column leaning -0.9°, overhanging top and bottom.
ctx.setFillColor(line); ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
box(W / 2, H / 2, 680 * s, H * 1.4, 0, -0.9, fill: bg)

// Card group: 2:1, offset left of the column's centre by the page's 45px.
let cw = 620 * s, ch = cw / 2
let cx = W / 2 - 45 * s, top = 46.0, cy = top + ch / 2
let left = cx - cw / 2
box(cx, cy, cw, ch, 24 * s, -1.4, fill: gold)
box(cx + 0.029 * cw, cy - 0.039 * ch, cw, ch, 24 * s, 0.7, stroke: line, width: 1.5 * s)

// Roux: 104% of the card's height at 2:3, 10% in from the right, 10% past the bottom.
let src = CGImageSourceCreateWithURL(input as CFURL, nil)!
let roux = CGImageSourceCreateImageAtIndex(src, 0, nil)!
let rh = 1.04 * ch, rw = rh * 2 / 3
let rx = left + cw - 0.10 * cw - rw, ry = top + ch + 0.10 * ch - rh
ctx.saveGState()
ctx.translateBy(x: rx, y: ry + rh); ctx.scaleBy(x: 1, y: -1)
ctx.draw(roux, in: CGRect(x: 0, y: 0, width: rw, height: rh))
ctx.restoreGState()

// Chips: the row under the card, a little closer than on the page to fit the frame.
let chip = 24 * s, gap = 11 * s, chipTop = top + ch + 80
for (i, c) in chipColors.enumerated() {
  let x = left + Double(i) * (chip + gap)
  box(x + chip / 2, chipTop + chip / 2, chip, chip, 5 * s, 0, fill: rgb(c))
  if i == chipColors.count - 1 {
    box(x + chip / 2, chipTop + chip / 2, chip, chip, 5 * s, 0, stroke: CGColor(gray: 0, alpha: 0.06), width: 1)
  }
}

let dest = CGImageDestinationCreateWithURL(output as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
CGImageDestinationFinalize(dest)
print("wrote \(output.path)")
