# KRT

### __Simple, small, interactive, console-based Python debugger.__
 - Cross-platform
 - Django compatibile

<br>

__KRT__ inherits from basic python debugger (called `bdb`). The main reason behind development of package was need of user interface during python script debugging in console (or when graphical interface is not available). Although `pdb` have the same (and propbably much more) functionality, I found it not so "user friendly".

<br>

###__Installation__

Install using `pip`.

```code
pip install krt
```

<br>

##__Basic script debugging__
```code
python krt.py script.py
# or
python -m krt script.py
```
 
 <br>
 
###__Initializing debugger during program execution__

This method of initialization allows initialization at specific line.

```python
import krt

def func(_something, _nothing):
  local_var = [1, 2, 3, 4]
  # now, initialize krt
  krt.trace()                   
  anything = _somethins + _nothing
  return anything
```

<br>

Initializing __krt__ via __@decorator__. This method will initialize __krt__ at 1st line of decorated method or function.

```python
import krt

# initialize krt
@krt.debug()
def func(_something, _nothing):
  local_var = [1, 2, 3, 4]
  anything = _somethins + _nothing
  return anything
```

<br>

##__Django usage__

One can use methods mentioned above, but method below allows __krt__ triggering only if run with pre-defined django command.

##### Setting up django command
1. Inside django applicaiton directory, create directory called `management`, inside which create directory `commands`.
   Following path, must exists `django_project/application/management/commands/`.
2. Create `__init__.py` inside `management` and `commands` directories.
3. Inside directory `commands`, create file `<command>.py`, where `<command>` will be used with `manage.py`.
   Let's say that we've used `krt_runserver.py`.
4. Insert into created file:
```python
 from django.core.management.base import BaseCommand
 from django.core.management.commands import runserver

 class Command(runserver.Command):
     help = "Sets trigger for krt decorators"

     def __init__(self, *args, **kwargs):
         from django.conf import settings
         setattr(settings, 'krt_django_decorator_trigger_flag', True)
         super(Command, self).__init__(*args, **kwargs)
```
<br>

##### Use decorator inside view

Decorator, when used in django project, requires setting of keyword argument `django` to `True`. If the `django` argument is omitted, the debugger will be __always initialized__!

```python
 from django.http import HttpResponse
 from  krttest.krt import debug

 @debug(django=True)
 def index(request):
     return HttpResponse("I'm ok.")
```
<br>

Now, when the django server is run with created command, __KRT__ debugger is being initialized on 1st line of view, otherwise the decorators are being ignored.
```code
python ./manage.py krt_runserver
```
<br>

__Key controls and commands__
```text
  [ ]next (enter pressed)    Evaluate current line and go to next line.
  [s]tep-in                  Step inside if callable, else go to next line.
  [r]eturn                   Return from call to outer frame.

  [j]ump [<file>] ['disp'] <line> <verbose>

                             Jump to line in current file. Setting verbose to True or 1
                             will perform jump in 'visible' mode. This mode can take
                             certain amount of time to complete. Consider turning off
                             code display.

                             When 'disp' is stated, the number refers to dispatch number,
                             counted from beginning of program evaluation. Using dispatch
                             jumping in combination with line jumping will NOT work.

                             Use '.' as reference to currently debugged file.

                             Examples:
                                 $ jump . 20
                                 $ jump disp 3000 True
                                 $ jump 20
                                 $ jump disp 300

  [c]ontinue                 Continue evaluation of file.
  [w]atch <variable>         Add local 'variable' to watches.
  [u]n-watch <variable>      Remove local 'variable' from watches.
  [o]utput                   Show / hide output of debugged program (replaces whole ui).
  [v]ars                     Show / hide local variables.
  [st]ack                    Show / hide current stack of stack frames.
  [co]de                     Show / hide code display.
  [re]size                   Adjust number of lines of code display.
  [h]elp                     Display small / large help panel.
  [q]uit                     Leave debugger.
```
