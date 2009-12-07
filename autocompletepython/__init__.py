#-*- coding:utf-8 -*-

import gedit
import gtk
import re
from pycodecompletation import Completer


SIMPLE_WORD_SYNTAX = r'@?[a-zA-Z0-9à-úÀ-Ú_$]+'                                             # only characters
COMPOUND_WORD_SYNTAX = r'@?[a-zA-Z0-9_à-úÀ-Ú$]+(?:(?:://|::|->|:|/|@|\.)@?[a-zA-Z0-9_$]+)+'# characters and tokens
BEGINNING_OF_COMPOUND_WORD_SYNTAX = r'(?:@?[a-zA-Z0-9_$]+(?:://|::|->|:|/|@|\.))+'         # given a pos in a compound_word, what can it be at the left
MAX_COMPOSITION_TOKEN_SIZE = 3                                                             # here the longest token is ://
MAX_SUGGESTIONS = 50
MAX_SUGGESTIONS_BEFORE_USE_BREAKS = 20
MIN_CHARACTERS_BEFORE_AUTOCOMPLETE = 2
AUTOCOMPLETE_BREAKS = '._>:'   # must be a simple string, can NOT be a regular expression
RE_SIMPLE_WORD_SYNTAX = re.compile(SIMPLE_WORD_SYNTAX, re.UNICODE|re.MULTILINE)
RE_COMPOUND_WORD_SYNTAX = re.compile(COMPOUND_WORD_SYNTAX, re.UNICODE|re.MULTILINE)
RE_BEGINNING_OF_COMPOUND_WORD_SYNTAX = re.compile(BEGINNING_OF_COMPOUND_WORD_SYNTAX, re.UNICODE|re.MULTILINE)
SPACES = "  "
MARKER = "> "

class AutoCompleteWindowHelper(gtk.Window):
    """Tooltip-like window for displaying a completion."""
    def __init__(self, parent):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.set_transient_for(parent)
        self.set_border_width(1)
        bg = self.rc_get_style().text[gtk.STATE_NORMAL]
        self.modify_bg(gtk.STATE_NORMAL, bg)
        self.label = gtk.Label()
        inner_box = gtk.EventBox()
        inner_box.set_border_width(5)
        inner_box.add(self.label)
        outer_box = gtk.EventBox()
        outer_box.add(inner_box)
        self.add(outer_box)

    def set_font_description(self, font_desc):
        """Set the label's font description."""
        self.label.modify_font(font_desc)
    
    def get_size(self):
        """Get the size of the window."""
        width, height = self.label.size_request()
        return width + 6, height + 6

    def set_text(self, text):
        """Set the label text and resize the window."""
        self.resize(1, 1)
        self.label.set_text(text)
    
    def get_text(self):
        """Return the label text."""
        return self.label.get_text()

class AutoCompletePlugin(gedit.Plugin):
    """Automatically complete words with the Return key."""
    def __init__(self):
        gedit.Plugin.__init__(self)
        self.completion = None
        self.id_name = 'AutoCompletePluginID'
        self.tip = None
        self.window = None
        self.last_typed_line = None
        self.regex_completion = 0

    def activate(self, window):
        """Activate plugin."""
        self.window = window
        self.tip = AutoCompleteWindowHelper(window)
        
        l_ids = []
        for signal in ('tab-added', 'tab-removed'):
            method = getattr(self, 'on_window_' + signal.replace('-', '_'))
            l_ids.append(window.connect(signal, method))
        window.set_data(self.id_name, l_ids)
        
        for view in window.get_views():
            self.connect_view(view)
        
        for doc in window.get_documents():
            self.connect_document(doc)
            self.scan(doc)

    def cancel(self):
        """Hide the completion tip and return False."""
        self.hide_tip()
        return False
    
    def complete(self):
        """Complete the current word."""
        doc = self.window.get_active_document()
        if self.regex_completion:
            insert = doc.get_iter_at_mark(doc.get_insert())
            start = insert.copy()
            for i in range(0, self.regex_completion):
               start.backward_char()
            doc.delete(start, insert)
        doc.insert_at_cursor(self.completion)
    
    def connect_document(self, doc):
        """Connect to document's signals."""
        l_ids = []
        for signal in ('end-user-action', 'loaded'):
            method = getattr(self, 'on_document_' + signal.replace('-', '_'))
            l_ids.append(doc.connect(signal, method))
        doc.set_data(self.id_name, l_ids)
    
    def connect_view(self, view):
        """Connect to view's signals."""
        l_ids = []
        for signal in ('focus-out-event', 'key-press-event',):
            method = getattr(self, 'on_view_' + signal.replace('-', '_'))
            l_ids.append(view.connect(signal, method))
        view.set_data(self.id_name, l_ids)
    
    def deactivate(self, window):
        """Deactivate plugin."""
        self.hide_tip()
        widgets = [window] + window.get_views() + window.get_documents()
        for widget in widgets:
            l_ids = widget.get_data(self.id_name)
            for l_id in l_ids:
                widget.disconnect(l_id)
                widget.set_data(self.id_name, None)
        self.tip    = None
        self.window = None
    
    def hide_tip(self):
        """Hide the completion tip."""
        self.tip.hide()
        self.completion = None
    
    def on_document_end_user_action(self, doc):
        """Scan document for words."""
        current_position = doc.get_iter_at_mark(doc.get_insert())
        if self.last_typed_line != current_position.get_line():
            self.scan(doc)
        self.last_typed_line = current_position.get_line()
    
    def on_document_loaded(self, doc, *args):
        """Scan document for words."""
        self.scan(doc)
    
    def on_view_focus_out_event(self, view, event):
        """Hide the completion tip."""
        doc = view.get_buffer()
        self.scan(doc)
        self.hide_tip()

    
    def re_contains_filter(self, list_to_filter, reference_item):
        new_list = list()
        reference_item_case_insensitive = ''
        for c in reference_item:
           if (c>='a' and c<='z') or (c>='A' and c<='Z'):
              reference_item_case_insensitive += '['+c.lower()+c.upper()+']'
           else:
              reference_item_case_insensitive += c
        for item in list_to_filter:
               if not RE_COMPOUND_WORD_SYNTAX.match(item) and re.findall(reference_item_case_insensitive, item):
                  new_list.append(item)
        return new_list

    def on_view_key_press_event(self, view, event):
        """Display a completion or complete the current word."""
        if event.state & gtk.gdk.CONTROL_MASK:
            return self.cancel()
        if event.state & gtk.gdk.MOD1_MASK and event.string != '/':
            return self.cancel()
        
        key = gtk.gdk.keyval_name(event.keyval)
        if  key == 'Return':
            if self.completion is None:
                return self.cancel()
            self.complete()
            complete_key_pressed = True
        else:
            complete_key_pressed = False
        
        # Select the next word in the list if Down MARKER pressed.
        if gtk.gdk.keyval_name(event.keyval) == 'Down':
            if self.completion is None:
                return self.cancel()
            self.select_alternative('Down')
            return True
        
        # Select the next word in the list if Up arrrow  pressed.
        if gtk.gdk.keyval_name(event.keyval) == 'Up':
            if self.completion is None:
                return self.cancel()
            self.select_alternative('Up')
            return True
       
        # Require input of one alphanumeric character or BackSpace.
        doc = view.get_buffer()
        insert = doc.get_iter_at_mark(doc.get_insert())
        if event.keyval>=128: # non-alphanumeric key
            if gtk.gdk.keyval_name(event.keyval) == 'BackSpace':
                doc = view.get_buffer()
                insert = doc.get_iter_at_mark(doc.get_insert())
                insert.backward_char()
                
            elif not complete_key_pressed:
                return self.cancel()
        
        selection_iters = view.get_buffer().get_selection_bounds()
        if selection_iters:
           regex_word = doc.get_text(selection_iters[0], selection_iters[1], False)
        else:
           start = insert.copy()
           while not start.is_start():
              start.backward_char()
              if re.match("\s", start.get_char()):
                 start.forward_char()
                 break
           regex_word = doc.get_text(start, insert, False)
        
        start = insert.copy()
        while start.backward_char():
            match_list = RE_SIMPLE_WORD_SYNTAX.findall(doc.get_text(start, insert, False))
            if len(match_list)==1 and len(match_list[0]) == len(doc.get_text(start, insert, False)):
                continue
            else:
                start.forward_char()
                break
        incomplete_simple_word = doc.get_text(start, insert, False)
        if not complete_key_pressed:
            incomplete_simple_word += event.string
        
        start_compound = start.copy()
        match_success = True
        while match_success == True:
           match_success = False
           if start.is_start():
              break
           for i in range(0, MAX_COMPOSITION_TOKEN_SIZE+1):  # +1: need to catch the char before the token
              start.backward_char()
              match_list = RE_BEGINNING_OF_COMPOUND_WORD_SYNTAX.findall(doc.get_text(start, start_compound, False))
              if len(match_list)==1 and len(match_list[0]) == len(doc.get_text(start, start_compound, False)):
                 match_success = True
                 break
        for i in range(0, MAX_COMPOSITION_TOKEN_SIZE+1):
            start.forward_char()
        incomplete_compound_word = doc.get_text(start, insert, False)
        if not complete_key_pressed:
            incomplete_compound_word += event.string
        
        if MIN_CHARACTERS_BEFORE_AUTOCOMPLETE < len(incomplete_compound_word):
            if incomplete_compound_word.strip().startswith("self."):
                text = doc.get_text(*doc.get_bounds())
                current_position = doc.get_iter_at_mark(doc.get_insert())
                lines = text.split("\n")
                linenumber = current_position.get_line()
                for line in lines[:linenumber:-1]:
                    if line.startswith('class '):
                        classname = re.search("(?!class\ ) [^\:\(]*", line).group().strip()
                        incomplete_compound_word.replace("self.", classname+'.').strip()
                        break
            compound_word_alternatives = [
                (incomplete_compound_word+info_item['word']).strip()
                    for info_item in self.completer.get_completions(incomplete_compound_word,'')
                        if not info_item['word'].startswith('__')]
            compound_word_alternatives.sort()
        else:
            compound_word_alternatives = []
        alternatives = compound_word_alternatives
        incomplete = incomplete_compound_word
        
        if event.string == '/' and event.state & gtk.gdk.MOD1_MASK:
            words_containing_regex = self.re_contains_filter(alternatives, regex_word)
            alternatives = words_containing_regex
            incomplete = ""
            self.regex_completion = len(regex_word)
        else:
            self.regex_completion = 0
        
        self.complete_word = None
        display_string = ""
        alternatives_counter = 0
        for word in alternatives:
            if not self.complete_word:
                self.complete_word = word
                display_string += MARKER
            else:
                display_string += SPACES
            display_string = display_string + word + "\n"
            alternatives_counter += 1
            if alternatives_counter == MAX_SUGGESTIONS: break
        
        if gtk.gdk.keyval_name(event.keyval) == 'BackSpace':
            insert.forward_char()
        
        if self.complete_word is None:
            self.cancel()
            if complete_key_pressed:
                return True
            else:
                return False
        # Display the completion tip near the insert iter.
        self.completion = self.complete_word[len(incomplete):]
        window = gtk.TEXT_WINDOW_TEXT
        rect = view.get_iter_location(insert)
        x, y = view.buffer_to_window_coords(window, rect.x, rect.y)
        x, y = view.translate_coordinates(self.window, x, y)
        self.show_tip(display_string.rstrip(), x, y)
        
        if complete_key_pressed: 
            return True
        else:
            return False
    
    
    def on_window_tab_added(self, window, tab):
        """Connect the document and view in tab."""
        context = tab.get_view().get_pango_context()
        font_desc = context.get_font_description()
        self.tip.set_font_description(font_desc)
        self.connect_document(tab.get_document())
        self.connect_view(tab.get_view())
    
    
    def on_window_tab_removed(self, window, tab):
        """Remove document's word set."""
        pass
    
    def scan(self, doc):
        """Scan document for new words."""
        text = doc.get_text(*doc.get_bounds())
        current_position = doc.get_iter_at_mark(doc.get_insert())
        line = current_position.get_line()
        self.completer = Completer()
        self.completer.evalsource(text, line)
        self.dictionary_words = ['teste1', 'teste2']

    def show_tip(self, text, x, y):
        """Show a completion tip in the main window's coordinates."""
        root_x, root_y = self.window.get_position()
        self.tip.move(root_x + x + 48, root_y + y + 48)
        self.tip.set_text(text)
        self.tip.show_all()

    def refresh_tip_on_complete(self):
        """Refresh the alternative word list when 'Tab' is pressed and a completion is done."""
        display_string = ""
        local_complete_word = self.complete_word
        for current_line in (self.tip.get_text() + "\n").splitlines(True): #!!!
            if current_line.startswith(SPACES + local_complete_word):
                if display_string == "":
                    display_string += current_line.replace(SPACES, MARKER)
                    self.completion = current_line.strip()[len(local_complete_word):]
                    self.complete_word = current_line.strip(" \n")
                else:
                    display_string += current_line
        if len(display_string) != 0:
            self.tip.set_text(display_string.rstrip("\n"))
        else:
            self.hide_tip()
        return True

    def select_alternative(self, direction=None):
        """Makes all the necessary modifications when an alternative word is selected from the list."""
        display_string = self.tip.get_text() + "\n"
        previous_line = ""
        first_line = None
        marker_moved = False
        display_lines = display_string.splitlines(True)
        if len(display_lines)==1: return True
        
        for current_line in display_lines: 
            if first_line is None:
                first_line = current_line
            if direction == "Down":
                if previous_line == MARKER + self.complete_word + "\n":
                    marker_moved = True
                    display_string = display_string.replace(previous_line, previous_line.replace(MARKER, SPACES))
                    display_string = display_string.replace(current_line, current_line.replace(SPACES, MARKER))
                    self.completion = current_line.strip()[len(self.complete_word)-len(self.completion):]
                    self.complete_word = current_line.strip()
                    break
            if direction == "Up":
                if current_line == MARKER + self.complete_word + "\n" and previous_line != "":
                    marker_moved = True
                    display_string = display_string.replace(current_line, current_line.replace(MARKER, SPACES))
                    display_string = display_string.replace(previous_line, previous_line.replace(SPACES, MARKER))
                    self.completion = previous_line.strip()[len(self.complete_word)-len(self.completion):]
                    self.complete_word = previous_line.strip()
                    break
            previous_line = current_line
        if not marker_moved:
            if direction == 'Down':
                display_string = display_string.replace(current_line, current_line.replace(MARKER, SPACES))
                display_string = display_string.replace(first_line, first_line.replace(SPACES, MARKER))
                self.completion = first_line.strip()[len(self.complete_word)-len(self.completion):]
                self.complete_word = first_line.strip()
            if direction == 'Up':
                display_string = display_string.replace(current_line, current_line.replace(SPACES, MARKER))
                display_string = display_string.replace(first_line, first_line.replace(MARKER, SPACES))
                self.completion = current_line.strip()[len(self.complete_word)-len(self.completion):]
                self.complete_word = current_line.strip()
        self.tip.set_text(display_string.rstrip("\n")) 
        return True
