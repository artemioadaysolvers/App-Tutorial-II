package com.montecarlolab

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Typeface
import android.view.View
import com.facebook.react.ReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReadableArray
import com.facebook.react.uimanager.SimpleViewManager
import com.facebook.react.uimanager.ThemedReactContext
import com.facebook.react.uimanager.ViewManager
import com.facebook.react.uimanager.annotations.ReactProp
import kotlin.math.*

/** Android Canvas renderer. No browser, JavaScript rendering engine or WebGL. */
class JointHistogramView(context: Context) : View(context) {
  var cells: List<DoubleArray> = emptyList()
  var dimensions = 2
  var bins = 5
  var ink = Color.rgb(46,73,58)
  var angle = 35.0
  var maximum = .01
  private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
  private data class Point(val x: Double, val y: Double, val z: Double)
  private data class Face(val points: List<Point>, val shade: Double, val alpha: Int, val depth: Double)
  private var scale = 1.0
  private fun rotate(p: Point): Point {
    val a = angle * Math.PI / 180
    return Point(p.x*cos(a)-p.y*sin(a), p.x*sin(a)+p.y*cos(a), p.z)
  }
  private fun screen(p: Point): Pair<Float,Float> {
    val r=rotate(p)
    return Pair((width*.5+r.x*scale).toFloat(), (height*.65+(r.y*.38-r.z*.85)*scale).toFloat())
  }
  private fun shade(factor: Double): Int = Color.rgb(
    (Color.red(ink)*factor).toInt().coerceIn(0,255),
    (Color.green(ink)*factor).toInt().coerceIn(0,255),
    (Color.blue(ink)*factor).toInt().coerceIn(0,255))
  override fun onDraw(canvas: Canvas) {
    super.onDraw(canvas)
    if (width==0 || height==0) return
    scale=min(width*.65,height*.64)
    val faces=mutableListOf<Face>()
    val peak=maximum.coerceAtLeast(.01)
    for (cell in cells) {
      val x=cell[0]/bins-.5; val y=cell[1]/bins-.5
      val z=if(dimensions==3)cell[2]/bins else 0.0
      val span=.90/bins
      val top=if(dimensions==3)z+span else cell[3]/peak*.8
      val points=listOf(Point(x,y,z),Point(x+span,y,z),Point(x+span,y+span,z),Point(x,y+span,z),
        Point(x,y,top),Point(x+span,y,top),Point(x+span,y+span,top),Point(x,y+span,top))
      val alpha=if(dimensions==3)(65+190*cell[3]/peak).toInt().coerceIn(65,255) else 255
      // All six faces are depth-sorted for an orthographic painter projection.
      val sides=listOf(listOf(0,1,2,3),listOf(0,1,5,4),listOf(1,2,6,5),
        listOf(2,3,7,6),listOf(3,0,4,7),listOf(4,5,6,7))
      for ((i,indices) in sides.withIndex()) {
        val vertices=indices.map{points[it]}
        val depth=vertices.map{val r=rotate(it);r.y*.85+r.z*.38}.average()
        faces.add(Face(vertices, listOf(.6,.75,.88,.75,.88,1.18)[i],alpha,depth))
      }
    }
    // Floor grid first, including empty bins.
    paint.color=Color.rgb(180,184,170);paint.alpha=120;paint.strokeWidth=resources.displayMetrics.density
    for (i in 0..bins) {
      val q=i.toDouble()/bins-.5
      line(canvas,Point(-.5,q,0.0),Point(.5,q,0.0))
      line(canvas,Point(q,-.5,0.0),Point(q,.5,0.0))
    }
    for (face in faces.sortedBy{it.depth}) {
      val path=Path()
      face.points.forEachIndexed{i,p->val (sx,sy)=screen(p);if(i==0)path.moveTo(sx,sy)else path.lineTo(sx,sy)}
      path.close()
      paint.style=Paint.Style.FILL;paint.color=shade(face.shade);paint.alpha=face.alpha
      canvas.drawPath(path,paint)
      paint.style=Paint.Style.STROKE;paint.color=Color.rgb(245,241,231);paint.alpha=75
      canvas.drawPath(path,paint)
    }
    paint.style=Paint.Style.FILL;paint.color=Color.rgb(41,58,48);paint.alpha=255
    paint.textSize=12*resources.displayMetrics.scaledDensity;paint.typeface=Typeface.MONOSPACE
    val origin=Point(-.58,-.58,0.0)
    for ((end,label) in listOf(Pair(Point(.7,-.58,0.0),"X"),Pair(Point(-.58,.7,0.0),"Y"),
      Pair(Point(-.58,-.58,1.05),if(dimensions==3)"Z" else "f"))) {
      line(canvas,origin,end)
      val (sx,sy)=screen(end)
      canvas.drawText(label,sx.coerceIn(6f,width-22f),sy.coerceIn(20f,height-6f),paint)
    }
  }
  private fun line(canvas:Canvas,a:Point,b:Point) {
    val (x1,y1)=screen(a);val(x2,y2)=screen(b)
    canvas.drawLine(x1,y1,x2,y2,paint)
  }
}

class JointHistogramManager : SimpleViewManager<JointHistogramView>() {
  override fun getName() = "AzarJointHistogram"
  override fun createViewInstance(context: ThemedReactContext) = JointHistogramView(context)
  @ReactProp(name="cells") fun setCells(view:JointHistogramView, array:ReadableArray?) {
    view.cells=(0 until (array?.size() ?: 0)).mapNotNull { i ->
      val a=array?.getArray(i)
      if(a==null||a.size()!=4) null else DoubleArray(4){a.getDouble(it)}
    };view.invalidate()
  }
  @ReactProp(name="dimensions",defaultInt=2) fun setDimensions(view:JointHistogramView,value:Int){view.dimensions=value.coerceIn(2,3);view.invalidate()}
  @ReactProp(name="bins",defaultInt=5) fun setBins(view:JointHistogramView,value:Int){view.bins=value.coerceIn(1,12);view.invalidate()}
  @ReactProp(name="ink") fun setInk(view:JointHistogramView,value:String?){view.ink=try{Color.parseColor(value)}catch(_:Exception){Color.rgb(46,73,58)};view.invalidate()}
  @ReactProp(name="angle",defaultDouble=35.0) fun setAngle(view:JointHistogramView,value:Double){view.angle=value;view.invalidate()}
  @ReactProp(name="maximum",defaultDouble=.01) fun setMaximum(view:JointHistogramView,value:Double){view.maximum=value;view.invalidate()}
}
class JointHistogramPackage : ReactPackage {
  override fun createNativeModules(context:ReactApplicationContext): List<NativeModule> = emptyList()
  override fun createViewManagers(context:ReactApplicationContext): List<ViewManager<*,*>> = listOf(JointHistogramManager())
}
