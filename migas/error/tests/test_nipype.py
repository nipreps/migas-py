import sys

from migas.error.nipype import node_execution_error

ERROR_TEXT = """
nipype.pipeline.engine.nodes.NodeExecutionError: Exception raised while executing Node failingnode.

Cmdline:
	mri_convert --out_type mgz --input_volume /tmp/sample/file.txt --output_volume /tmp/wf/conv1/README_out.mgz
Stdout:
	mri_convert --out_type mgz --input_volume /tmp/sample/file.txt --output_volume /tmp/wf/conv1/README_out.mgz
	ERROR: cannot determine file type for /tmp/sample/file.txt
Stderr:

Traceback:
	Traceback (most recent call last):
	  File "/code/nipype/nipype/interfaces/base/core.py", line 454, in aggregate_outputs
	    setattr(outputs, key, val)
	  File "/code/nipype/nipype/interfaces/base/traits_extension.py", line 425, in validate
	    value = super(MultiObject, self).validate(objekt, name, newvalue)
	  File "/code/.pyenv/versions/nipreps/lib/python3.10/site-packages/traits/trait_types.py", line 2699, in validate
	    return TraitListObject(self, object, name, value)
	  File "/code/.pyenv/versions/nipreps/lib/python3.10/site-packages/traits/trait_list_object.py", line 582, in __init__
	    super().__init__(
	  File "/code/.pyenv/versions/nipreps/lib/python3.10/site-packages/traits/trait_list_object.py", line 213, in __init__
	    super().__init__(self.item_validator(item) for item in iterable)
	  File "/code/.pyenv/versions/nipreps/lib/python3.10/site-packages/traits/trait_list_object.py", line 213, in <genexpr>
	    super().__init__(self.item_validator(item) for item in iterable)
	  File "/code/.pyenv/versions/nipreps/lib/python3.10/site-packages/traits/trait_list_object.py", line 865, in _item_validator
	    return trait_validator(object, self.name, value)
	  File "/code/nipype/nipype/interfaces/base/traits_extension.py", line 330, in validate
	    value = super(File, self).validate(objekt, name, value, return_pathlike=True)
	  File "/code/nipype/nipype/interfaces/base/traits_extension.py", line 135, in validate
	    self.error(objekt, name, str(value))
	  File "/code/.pyenv/versions/nipreps/lib/python3.10/site-packages/traits/base_trait_handler.py", line 74, in error
	    raise TraitError(
	traits.trait_errors.TraitError: Each element of the 'out_file' trait of a MRIConvertOutputSpec instance must be a pathlike object or string representing an existing file, but a value of '/tmp/wf/conv1/README_out.mgz' <class 'str'> was specified.

	During handling of the above exception, another exception occurred:

	Traceback (most recent call last):
	  File "/code/nipype/nipype/interfaces/base/core.py", line 401, in run
	    outputs = self.aggregate_outputs(runtime)
	  File "/code/nipype/nipype/interfaces/base/core.py", line 461, in aggregate_outputs
	    raise FileNotFoundError(msg)
	FileNotFoundError: No such file or directory '/tmp/wf/conv1/README_out.mgz' for output 'out_file' of a MRIConvert interface
"""


class NodeExecutionError(Exception):
    ...


TB = None
try:
    1 + 'a'
except Exception:
    _, _, TB = sys.exc_info()


def test_node_execution_error():
    kwargs = node_execution_error(NodeExecutionError, ERROR_TEXT, TB)
    assert kwargs['status'] == 'F'
    assert kwargs['error_type'] == 'NodeExecutionError'
    assert 'FileNotFoundError' in kwargs['error_desc']
