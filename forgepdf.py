import sys
from pathlib import Path
import pymupdf as fitz
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QImage, QPixmap
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,
    QListWidget,QPushButton,QFileDialog,QMessageBox,QInputDialog,QScrollArea,QToolBar)

class ForgePDF(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ForgePDF Editor — Local PDF Workspace")
        self.resize(1200,850)
        self.doc=fitz.open()
        self.current=0
        self.path=None
        self.mode=None
        self.zoom=1.25
        self.make_ui()
    def make_ui(self):
        bar=QToolBar("Tools")
        self.addToolBar(bar)
        for label,method in [("Open",self.open_pdf),("Merge",self.merge),("Save As",self.save_as),
                             ("Extract",self.extract),("Delete",self.delete_page),
                             ("Rotate",self.rotate),("Move Up",lambda:self.move(-1)),
                             ("Move Down",lambda:self.move(1)),("Add Text",lambda:self.set_mode("text")),
                             ("Replace Text",self.replace_text),("Text Field",lambda:self.set_mode("field")),
                             ("Signature Field",lambda:self.set_mode("signature")),
                             ("CAC Sign",self.cac_sign)]:
            a=QAction(label,self);a.triggered.connect(method);bar.addAction(a)
        root=QWidget();self.setCentralWidget(root)
        layout=QHBoxLayout(root)
        left=QVBoxLayout();layout.addLayout(left,1)
        left.addWidget(QLabel("Pages (select to preview)"))
        self.pages=QListWidget();self.pages.currentRowChanged.connect(self.select_page)
        left.addWidget(self.pages)
        self.viewer=QLabel("Open a PDF to begin")
        self.viewer.setAlignment(Qt.AlignCenter)
        self.viewer.setStyleSheet("background:#343b4b;color:white;")
        self.viewer.mousePressEvent=self.canvas_click
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.viewer)
        layout.addWidget(scroll,4)
        self.statusBar().showMessage("Local processing only. Finish editing before CAC signing.")
    def set_mode(self,mode):
        if not self.doc.page_count:return
        self.mode=mode
        self.statusBar().showMessage("Click a location on the page to place "+mode)
    def refresh(self,selected=None):
        self.pages.blockSignals(True)
        self.pages.clear()
        for i in range(self.doc.page_count):self.pages.addItem(f"Page {i+1}")
        self.pages.blockSignals(False)
        self.current=max(0,min(selected if selected is not None else self.current,self.doc.page_count-1))
        if self.doc.page_count:
            self.pages.setCurrentRow(self.current)
            self.render()
        else:self.viewer.setText("No pages")
    def render(self):
        if not self.doc.page_count:return
        page=self.doc[self.current]
        pix=page.get_pixmap(matrix=fitz.Matrix(self.zoom,self.zoom),alpha=False)
        image=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format_RGB888).copy()
        self.viewer.setPixmap(QPixmap.fromImage(image))
        self.viewer.setFixedSize(pix.width,pix.height)
        self.statusBar().showMessage(f"Page {self.current+1}/{self.doc.page_count} | {self.mode or 'Browse'}")
    def select_page(self,row):
        if row>=0 and row<self.doc.page_count:self.current=row;self.render()
    def open_pdf(self):
        path,_=QFileDialog.getOpenFileName(self,"Open PDF","","PDF (*.pdf)")
        if not path:return
        try:
            new=fitz.open(path)
            if new.needs_pass:raise ValueError("Password-protected PDF is not supported in this version.")
            self.doc.close();self.doc=new;self.path=path;self.refresh(0)
        except Exception as e: self.error(e)
    def merge(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Append PDFs","","PDF (*.pdf)")
        if not paths:return
        try:
            for path in paths:
                with fitz.open(path) as source:
                    if source.needs_pass:raise ValueError(f"Encrypted PDF: {path}")
                    self.doc.insert_pdf(source,widgets=True)
            self.refresh()
        except Exception as e:self.error(e)
    def save_as(self):
        if not self.doc.page_count:return
        path,_=QFileDialog.getSaveFileName(self,"Save PDF",self.path or "document.pdf","PDF (*.pdf)")
        if not path:return
        try:
            if self.path and Path(path).resolve()==Path(self.path).resolve():
                raise ValueError("Choose a different filename to preserve the original.")
            self.doc.save(path,garbage=4,deflate=True)
            self.path=path
            self.statusBar().showMessage("Saved: "+path)
        except Exception as e:self.error(e)
    def extract(self):
        if not self.doc.page_count:return
        spec,ok=QInputDialog.getText(self,"Extract pages","Page numbers/ranges (e.g. 1,3-5):")
        if not ok:return
        try:
            indices=set()
            for part in spec.split(","):
                bits=part.strip().split("-")
                a=int(bits[0]);b=int(bits[-1])
                if a<1 or b<a or b>self.doc.page_count:raise ValueError("Invalid page range")
                indices.update(range(a-1,b))
            path,_=QFileDialog.getSaveFileName(self,"Save extracted pages","extracted.pdf","PDF (*.pdf)")
            if not path:return
            out=fitz.open()
            for i in sorted(indices):out.insert_pdf(self.doc,from_page=i,to_page=i)
            out.save(path);out.close()
        except Exception as e:self.error(e)
    def delete_page(self):
        if not self.doc.page_count:return
        if QMessageBox.question(self,"Delete","Delete selected page?")!=QMessageBox.Yes:return
        self.doc.delete_page(self.current);self.refresh()
    def rotate(self):
        if not self.doc.page_count:return
        p=self.doc[self.current];p.set_rotation((p.rotation+90)%360);self.render()
    def move(self,delta):
        a=self.current;b=a+delta
        if b<0 or b>=self.doc.page_count:return
        order=list(range(self.doc.page_count));order.insert(b,order.pop(a))
        self.doc.select(order);self.refresh(b)
    def canvas_click(self,event):
        if not self.mode or not self.doc.page_count:return
        pos=event.position()
        x=pos.x()/self.zoom;y=pos.y()/self.zoom
        page=self.doc[self.current]
        try:
            if self.mode=="text":
                value,ok=QInputDialog.getMultiLineText(self,"Add text","Text:")
                if ok and value:page.insert_text((x,y),value,fontsize=11)
            elif self.mode=="field":
                name,ok=QInputDialog.getText(self,"Text field","Field name:")
                if ok and name:
                    widget=fitz.Widget();widget.field_name=name
                    widget.field_type=fitz.PDF_WIDGET_TYPE_TEXT
                    widget.rect=fitz.Rect(x,y,x+210,y+28)
                    widget.border_color=(0.3,0.3,0.3);widget.border_width=1
                    page.add_widget(widget)
            elif self.mode=="signature":
                from pyhanko.sign.fields import append_signature_field, SigFieldSpec
                from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
                import io
                name,ok=QInputDialog.getText(self,"Signature field","Unique field name:","QLineEdit.Normal","Signature1")
                if ok and name:
                    data=self.doc.tobytes(garbage=3,deflate=True)
                    writer=IncrementalPdfFileWriter(io.BytesIO(data))
                    append_signature_field(writer,SigFieldSpec(sig_field_name=name,on_page=self.current,box=(int(x),int(page.rect.height-y-55),int(x+230),int(page.rect.height-y))))
                    output=io.BytesIO();writer.write(output)
                    new=fitz.open(stream=output.getvalue(),filetype="pdf")
                    self.doc.close();self.doc=new
            self.mode=None;self.refresh()
        except Exception as e:self.mode=None;self.error(e)
    def replace_text(self):
        if not self.doc.page_count:return
        old,ok=QInputDialog.getText(self,"Replace text","Exact text to replace on current page:")
        if not ok or not old:return
        new,ok=QInputDialog.getText(self,"Replace text","Replacement text:")
        if not ok:return
        page=self.doc[self.current]
        matches=page.search_for(old)
        if not matches:QMessageBox.information(self,"No matches","No matching selectable text on this page.");return
        if QMessageBox.question(self,"Confirm replacement",f"Replace {len(matches)} match(es)? This removes underlying content in those regions and may change formatting.")!=QMessageBox.Yes:return
        for rect in matches:page.add_redact_annot(rect,fill=(1,1,1))
        page.apply_redactions(images=0,graphics=0)
        for rect in matches:
            page.insert_text((rect.x0,rect.y1-2),new,fontsize=max(6,min(12,rect.height*0.8)))
        self.render()
    def cac_sign(self):
        if not self.doc.page_count:return
        QMessageBox.information(self,"CAC signing setup",
            "CAC signing needs PKCS#11 middleware and certificate selection. "
            "This initial build can create PDF signature fields, but does not yet perform CAC cryptographic signing. "
            "Do not treat an unsigned signature field as a signed document.")
    def error(self,error):QMessageBox.critical(self,"ForgePDF error",str(error))

if __name__=="__main__":
    app=QApplication(sys.argv)
    window=ForgePDF();window.show()
    sys.exit(app.exec())
