from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import torch
from torch.nn.parallel.scatter_gather import scatter, gather


class GraphDataParallel(torch.nn.parallel.DataParallel):
    # FIXME TODO Assumes network has a single input for now
    # TODO add a case for dict
    def __init__(self, module, device_ids=None, output_device=None, dim=0):
        super(GraphDataParallel, self).__init__(module,
                                                device_ids=device_ids,
                                                output_device=output_device,
                                                dim=dim)
    def scatter(self, inputs, kwargs, device_ids):
        """
        len(inputs) = how many inputs the network takes
        len(inputs[0]) = #GPUs * mbs
        """
        final_inputs = []
        if len(inputs[0]) % len(device_ids) != 0:
            raise Exception("Number of inputs must be a multiple of number of devices")

        minibatch_size = int(len(inputs[0]) / len(device_ids))
        for i, device in enumerate(device_ids):
            input_i = inputs[0][i*minibatch_size:(i+1)*minibatch_size]
            if len(input_i) == 1:
                input_i = input_i[0]
            final_inputs += scatter(input_i, [device], self.dim) if inputs else []
        if len(device_ids) == 1:
            final_inputs = [final_inputs]
        final_kwargs = scatter(kwargs, device_ids, self.moduledim) if kwargs else []
        if len(final_inputs) < len(final_kwargs):
            final_inputs.extend([() for _ in range(len(final_kwargs) - len(final_inputs))])
        elif len(final_kwargs) < len(final_inputs):
            final_kwargs.extend([{} for _ in range(len(final_inputs) - len(final_kwargs))])
        final_inputs = tuple(final_inputs)
        final_kwargs = tuple(final_kwargs)

        return final_inputs, final_kwargs

    def gather(self, outputs, output_device):
        """
        len(outputs) = number of gpus
        len(outputs[0]) = minibatch size
        Returns a tuple of length the number of objects returned by network
        Length of tuple[0] = number of gpus
        """
        results = []
        for output in outputs:  # Iterate over GPUs
            network_outputs = gather([output], output_device, dim=self.dim)
            results.extend(network_outputs)
        return results
