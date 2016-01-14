"""
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import remi.gui as gui
from remi import start, App
import imp
import os #for path handling
import prototypes
import editor_widgets


class Dragable(gui.Widget):
    def __init__(self, w, h):
        super(Dragable, self).__init__(w, h)
        self.style['position'] = 'relative'
        self.style['user-select'] = 'none'
        self.attributes['draggable'] = 'true'
        self.attributes['ondragstart'] = "this.style.cursor='move';this.style['left']=(event.clientX - parseInt(this.style.width)/2) + 'px'; this.style['top']=(event.clientY - parseInt(this.style.height)/2) + 'px';'"
        self.attributes['ondragover'] = "this.style.cursor='move';event.dataTransfer.dropEffect = 'move';"   
        self.attributes['ondragend'] = "this.style.cursor='default';this.style['left']=(event.clientX - parseInt(this.style.width)/2) + 'px'; this.style['top']=(event.clientY - parseInt(this.style.height)/2) + 'px';"  
        

class ResizerHelper(gui.Widget):
    """ Allows to resize the widget to which it refers.
        Four grippers at four corners resizes the widget by dragging
    """
    def __init__(self):
        pass


class WidgetHelper(gui.ListItem):
    """ Allocates the Widget to which it refers, 
        interfacing to the user in order to obtain the necessary attribute values
        obtains the constructor parameters, asks for them in a dialog
        puts the values in an attribute called constructor
    """

    def __init__(self, w, h, widgetClass):
        self.widgetClass = widgetClass
        super(WidgetHelper, self).__init__(w, h, self.widgetClass.__name__)
            
    def allocate(self, appInstance):
        """ Here the widget is allocated and it is performed the setup to allow the
            selection and editing
            
            def func(a:'parameter A') -> 'return value':
            func.__annotations__ {'a': 'parameter A', 'return': 'return value'}
        """
        self.appInstance = appInstance
        param_as_string_list = self.widgetClass.__init__.__code__.co_varnames[1:] #[1:] removes the self
        param_annotation_dict = ''#self.widgetClass.__init__.__annotations__
        self.dialog = gui.GenericDialog(title=self.widgetClass.__name__, message='Fill the following parameters list')
        self.dialog.add_field_with_label('name', 'Variable name', gui.TextInput(200,30))
        for param in param_as_string_list:
            note = ''#" (%s)"%param_annotation_dict[param] if param in param_annotation_dict.keys() else ""
            self.dialog.add_field_with_label(param, param + note, gui.TextInput(200,30))
        self.dialog.set_on_confirm_dialog_listener(self, "on_dialog_confirm")
        self.dialog.show(self.appInstance)
        
    def on_dialog_confirm(self):
        param_as_string_list = self.widgetClass.__init__.__code__.co_varnames[1:] #[1:] removes the self
        param_annotation_dict = ''#self.widgetClass.__init__.__annotations__
        param_values = []
        for param in param_as_string_list:
            param_values.append(self.dialog.get_field(param).get_value())
            
        print(param_as_string_list)
        print(param_values)
        constructor = '%s(%s)'%(self.widgetClass.__name__, ','.join(map(lambda v: str(v), param_values)))
        #here we create and decorate the widget
        widget = self.widgetClass(*param_values)
        widget.attributes['editor_constructor'] = constructor
        widget.attributes['editor_varname'] = self.dialog.get_field('name').get_value()
        widget.attributes['editor_tag_type'] = 'widget'
        widget.attributes['editor_newclass'] = 'false'
        
        #drag properties
        widget.style['position'] = 'relative'
        widget.style['left'] = '0px'
        widget.style['top'] = '0px'
        widget.attributes['draggable'] = 'true'
        widget.attributes['ondragstart'] = """this.style.cursor='move'; event.dataTransfer.dropEffect = 'move';   event.dataTransfer.setData('application/json', JSON.stringify([event.target.id,(event.clientX),(event.clientY)]));"""
        widget.attributes['ondragover'] = "event.preventDefault();"   
        widget.attributes['ondrop'] = """event.preventDefault();return false;"""
        
        #"this.style.cursor='default';this.style['left']=(event.screenX) + 'px'; this.style['top']=(event.screenY) + 'px'; event.preventDefault();return true;"  
        
        self.appInstance.add_widget_to_editor(widget)
        

class WidgetCollection(gui.Widget):
    def __init__(self, w, h, appInstance):
        self.w = w
        self.h = h
        self.appInstance = appInstance
        super(WidgetCollection, self).__init__(w, h, gui.Widget.LAYOUT_VERTICAL, 0)
        
        self.lblTitle = gui.Label(self.w, 30, "Widgets Toolbox")
        self.listWidgets = gui.ListView(self.w, self.h-30)
        
        self.append(self.lblTitle)
        self.append(self.listWidgets)
        
        #load all widgets
        self.add_widget_to_collection(gui.Widget)
        self.add_widget_to_collection(gui.Button)
        self.add_widget_to_collection(gui.TextInput)
        self.add_widget_to_collection(gui.Label)
        self.add_widget_to_collection(gui.ListView)
        self.add_widget_to_collection(gui.ListItem)
        self.add_widget_to_collection(gui.DropDown)
        self.add_widget_to_collection(gui.DropDownItem)
        self.add_widget_to_collection(gui.Image)
        self.add_widget_to_collection(gui.CheckBoxLabel)
        self.add_widget_to_collection(gui.CheckBox)
        self.add_widget_to_collection(gui.SpinBox)
        self.add_widget_to_collection(gui.Slider)
        self.add_widget_to_collection(Dragable)
        
    def add_widget_to_collection(self, widgetClass):
        #create an helper that will be created on click
        #the helper have to search for function that have 'return' annotation 'event_listener_setter'
        helper = WidgetHelper(self.w, 30, widgetClass)
        self.listWidgets.append( helper )
        helper.set_on_click_listener(self.appInstance, "widget_helper_clicked")


def repr_widget_for_editor(widget): #widgetVarName is the name with which the parent calls this instance
    code_classes = ''
    code_nested = '' #the code strings to return
    
    if not hasattr( widget, 'attributes' ):
        return ('','')
    widgetVarName = widget.attributes['editor_varname']
    newClass = widget.attributes['editor_newclass'] == 'True'
    classname =  'CLASS' + widgetVarName if newClass else widget.__class__.__name__
    
    code_nested = prototypes.proto_widget_allocation%{'varname': widgetVarName, 'classname': classname, 'editor_constructor': widget.attributes['editor_constructor']}
    
    if newClass:
        widgetVarName = 'self'
            
    for key in widget.attributes.keys():
        code_nested += prototypes.proto_attribute_setup%{'varname': widgetVarName, 'attrname': key, 'attrvalue': widget.attributes[key]}
    
    children_code_nested = ''
    for child_key in widget.children.keys():
        child_ret = repr_widget_for_editor(widget.children[child_key])
        children_code_nested += child_ret[1]
        code_classes = child_ret[0] + code_classes
    
    if newClass:
        code_classes = prototypes.proto_code_class%{'classname': classname, 'superclassname': super(widget.__class__,widget).__class__.__name__,
                                                    'nested_code': children_code_nested }
    
    return (code_classes, code_nested)
    

class Project(gui.Widget):
    """ The editor project is pure html with specific tag attributes
        This class loads and save the project file, 
        and also compiles a project in python code.
    """
    def __init__(self, w, h, project_name='untitled'):
        super(Project, self).__init__(w, h, True, 0)
        
        self.project_name = project_name
        
        self.style['overflow'] = 'scroll'
        self.style['background-color'] = 'gray'
        self.style['background-image'] = "url( '/res/bg.png' );"
        self.soup = ''

        self.code_classes = ""
        #self.code_listenfunctions = ""
        self.code_resourcepath = "" #should be defined in the project configuration
        
        self.code_classes = {}
    
    def new(self):
        #remove the main widget
        pass
            
    def load(self, ifile):
        self.ifile = ifile
        #print("project name:%s"%os.path.basename(self.ifile))
        self.project_name = os.path.basename(self.ifile).replace('.py','')
        
        _module = imp.load_source('project', self.ifile) #imp.load_source('module.name', '/path/to/file.py')
        
        self.append( _module.load_project(), "root" )
        
    def save(self, code, _ifile=None): #the html will come back from the browser
        if _ifile is None:
            ifile = self.ifile
        
    def compile(self, save_path_filename, rootchild=None): 
        #the first child is the soup
        #returns code_constructors,code_layoutings, ode_listeners
        compiled_code=''
        code_constructors=''
        code_layoutings=''
        code_listeners=''
        
        ret = repr_widget_for_editor( self.children['root'] )
        compiled_code = ret[0]
        code_constructors = ret[1]
        main_code_class = prototypes.proto_code_main_class%{'classname':self.project_name,
                                                        'code_resourcepath':self.code_resourcepath,
                                                        'code_constructors':code_constructors, 
                                                        'code_layoutings':code_layoutings, 
                                                        'code_listeners':code_listeners,
                                                        'mainwidgetname':''}#child['editor_varname']}

        compiled_code += main_code_class
        print(compiled_code)
        if save_path_filename!=None:
            f = open(save_path_filename, "w")
            f.write(compiled_code)
            f.close()
            
        #returning code parts to the parent
        return ""
        
        
class Editor(App):
    def __init__(self, *args):
        super(Editor, self).__init__(*args)

    def main(self):
        self.mainContainer = gui.Widget(970, 700, gui.Widget.LAYOUT_VERTICAL, 0)
        self.mainContainer.style['background-color'] = 'white'
        self.mainContainer.style['border'] = 'none'
        
        menu = gui.Menu(950, 30)
        m1 = gui.MenuItem(100, 30, 'File')
        m10 = gui.MenuItem(100, 30, 'New')
        m11 = gui.MenuItem(100, 30, 'Open')
        m12 = gui.MenuItem(100, 30, 'Save')
        #m12.style['visibility'] = 'hidden'
        m13 = gui.MenuItem(100, 30, 'Compile')
        m121 = gui.MenuItem(100, 30, 'Save')
        m122 = gui.MenuItem(100, 30, 'Save as')
        m1.append(m10)
        m1.append(m11)
        m1.append(m12)
        m1.append(m13)
        m12.append(m121)
        m12.append(m122)
        
        m2 = gui.MenuItem(100, 30, 'Edit')
        m21 = gui.MenuItem(100, 30, 'Cut')
        m22 = gui.MenuItem(100, 30, 'Paste')
        m2.append(m21)
        m2.append(m22)
        
        menu.append(m1)
        menu.append(m2)
        
        self.fileOpenDialog = editor_widgets.EditorFileSelectionDialog(600, 310, 'Open Project', 'Select the project file', False, '.', True, False, self)
        self.fileOpenDialog.set_on_confirm_value_listener(self, 'on_open_dialog_confirm')
        
        self.fileSaveAsDialog = editor_widgets.EditorFileSaveDialog(600, 310, 'Project Save', 'Select the project folder and type a filename', False, '.', False, True, self)
        self.fileSaveAsDialog.add_fileinput_field('untitled.html')
        self.fileSaveAsDialog.set_on_confirm_value_listener(self, 'on_saveas_dialog_confirm')        
        
        self.fileCompileDialog = editor_widgets.EditorFileSaveDialog(600, 310, 'Project Compile', 'Select the folder and type a filename (extension .py)', False, '.', False, True, self)
        self.fileCompileDialog.add_fileinput_field('untitled.py')
        self.fileCompileDialog.set_on_confirm_value_listener(self, 'on_compile_dialog_confirm')        
        
        m10.set_on_click_listener(self, 'menu_new_clicked')
        m11.set_on_click_listener(self.fileOpenDialog, 'show')
        m121.set_on_click_listener(self, 'menu_save_clicked')
        m122.set_on_click_listener(self.fileSaveAsDialog, 'show')
        m13.set_on_click_listener(self.fileCompileDialog, 'show')
        m21.set_on_click_listener(self, 'menu_cut_selection_clicked')
        m22.set_on_click_listener(self, 'menu_paste_selection_clicked')
        
        self.subContainer = gui.Widget(970, 700, gui.Widget.LAYOUT_HORIZONTAL, 5)
        self.subContainer.style['background-color'] = 'transparent'
        
        #here are contained the widgets
        self.widgetsCollection = WidgetCollection(180, 600, self)
        self.project = Project(580, 600)
        self.project.attributes['ondragover'] = "event.preventDefault();"  
        self.project.attributes['ondrop'] = """event.preventDefault();
                var data = JSON.parse(event.dataTransfer.getData('application/json'));
                document.getElementById(data[0]).style.left = parseInt(document.getElementById(data[0]).style.left) + event.clientX - data[1] + 'px';
                document.getElementById(data[0]).style.top = parseInt(document.getElementById(data[0]).style.top) + event.clientY - data[2] + 'px';
                return false;"""
        self.attributeEditor = editor_widgets.EditorAttributes(180, 600)
        self.attributeEditor.set_on_attribute_change_listener(self, "on_attribute_change")
        self.mainContainer.append(menu)
        self.mainContainer.append(self.subContainer)
        
        self.subContainer.append(self.widgetsCollection)
        self.subContainer.append(self.project)
        self.subContainer.append(self.attributeEditor)
        
        self.tabindex = 0 #incremental number to allow widgets selection
        
        self.selectedWidget = self.project
        
        self.project.new()
        
        self.projectPathFilename = ''
        self.editCuttedWidget = None #cut operation, contains the cutted tag
        
        # returning the root widget
        return self.mainContainer

    # listener function
    def widget_helper_clicked(self, helperInstance):
        helperInstance.allocate(self)
    
    def configure_widget_for_editing(self, widget):
        typefunc = type(widget.onfocus)
        widget.onfocus = typefunc(onfocus_with_instance, widget)
        
        widget.set_on_focus_listener(self, "on_widget_selection")

        widget.attributes['contentEditable']='true';
        widget.attributes['tabindex']=str(self.tabindex)
        self.tabindex += 1
    
    def add_widget_to_editor(self, widget):
        self.configure_widget_for_editing(widget)
        self.selectedWidget.append(widget)
        
    def on_attribute_change(self, attributeName, value):
        self.selectedWidget.attributes[attributeName] = value
    
    def on_widget_selection(self, widget):
        self.selectedWidget = widget
        self.attributeEditor.set_widget( self.selectedWidget )

    def menu_new_clicked(self):
        self.project.new()

    def on_open_dialog_confirm(self, filelist):
        if len(filelist):
            self.project.load(filelist[0])
            self.projectPathFilename = filelist[0]
        
    def menu_save_clicked(self):
        if self.projectPathFilename == '':
            self.fileSaveAsDialog.show()
        else:
            self.project.save(self.projectPathFilename)
        
    def on_saveas_dialog_confirm(self, path):
        if len(path):
            self.projectPathFilename = path + '/' + self.fileSaveAsDialog.get_fileinput_value()
            print("file:%s"%filename)
            self.project.save(self.projectPathFilename)
        
    def on_compile_dialog_confirm(self, path):
        if len(path):
            filename = path + '/' + self.fileSaveAsDialog.get_fileinput_value()
            print("file:%s"%filename)
            self.project.compile(filename)
            
    def menu_cut_selection_clicked(self):
        #self.project.soup = BeautifulSoup(str(self.project.soup),'html.parser')
        self.editCuttedWidget = self.project.soup.find(id=self.selectedWidget).extract()
        print("tag cutted:" + str(id(self.editCuttedWidget)))

    def menu_paste_selection_clicked(self):
        if self.editCuttedWidget != None:
            self.selectedWidget.append(self.editCuttedWidget)
            self.editCuttedWidget = None


#function overload for widgets that have to be editable
#the normal onfocus function does not returns the widget instance
def onfocus_with_instance(self):
    return self.eventManager.propagate(self.EVENT_ONFOCUS, [self])
#def onclick_with_instance(self):
#    return self.eventManager.propagate(self.EVENT_ONCLICK, [str(id(self))])
        
if __name__ == "__main__":
    p = Project(0,0)
    p.load('./example_project.py')
    p.compile(None)
    # starts the webserver
    # optional parameters
    # start(MyApp,address='127.0.0.1', port=8081, multiple_instance=False,enable_file_cache=True, update_interval=0.1, start_browser=True)
    start(Editor, debug=False)
