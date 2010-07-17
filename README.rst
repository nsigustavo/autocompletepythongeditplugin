:author: Gustavo Rezende <nsigustavo@gmail.com>


Auto Complete Python - Gedit Plugin
===================================
Adds a popup dialog completition of code in gEdit. In order to play nice with snippets plugin, trigger is set to Enter.



Get and install
===============

You can download geditpyflakes::

    $ wget http://github.com/nsigustavo/autocompletepythongeditplugin/tarball/master
    $ tar -xzvf nsigustavo-autocompletepythongeditplugin*.tar.gz
    
Put the autocompletepython.gedit-plugin file and the whole content directory into ~/.gnome2/gedit/plugins::

    $ cd autocompletepythongeditplugin*
    $ mv autocompletepython*  ~/.gnome2/gedit/plugins/


Install dependence pycodecompletation::

    $ wget http://github.com/nsigustavo/pycodecompletation/tarball/master
    $ tar -xzvf nsigustavo-pycodecompletation*.tar.gz
    $ cd pycodecompletation*
    $ sudo python setup.py install


In gedit main menu go to: Edit -> Preferences

In Preferences dialog go to Plugins tab

Find 'Auto complete python' in plugin list and check it


