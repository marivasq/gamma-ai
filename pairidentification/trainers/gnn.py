"""
This module defines a generic trainer for simple models and datasets.
"""

# System
import time

# Externals
import torch
from torch import nn

# Locals
from .base_trainer import BaseTrainer
from models import get_model

class GNNTrainer(BaseTrainer):
    """Trainer code for basic classification problems."""

    def __init__(self, **kwargs):
        super(GNNTrainer, self).__init__(**kwargs)

    def build_model(self, model_type='gnn_segment_classifier',
                    optimizer='Adam', learning_rate=0.001,
                    loss_func='BCELoss', **model_args):
        """Instantiate our model"""
        self.model = get_model(name=model_type, **model_args).to(self.device)
        if self.distributed:
            self.model = nn.parallel.DistributedDataParallelCPU(self.model)
        self.optimizer = getattr(torch.optim, optimizer)(
            self.model.parameters(), lr=learning_rate)
        self.loss_func = getattr(torch.nn, loss_func)()
    
    def train_epoch(self, data_loader):
        """Train for one epoch"""
        self.model.train()
        summary = dict()
        sum_loss = 0
        start_time = time.time()
        i_final = 0
        # Loop over training batches
        for i, (batch_input, batch_target) in enumerate(data_loader):
            print('batch_input')
            print(batch_input)
            print(len(batch_input))
            print(batch_input[0].size())
            print(batch_input[1].size())
            print(batch_input[2].size())
            print('batch_target')
            print(batch_target)
            print(batch_target.size())
            self.logger.debug('  batch %i', i)
            batch_input = [a.to(self.device) for a in batch_input]
            batch_target = batch_target.to(self.device)
            self.model.zero_grad()
            batch_output = self.model(batch_input)
            batch_loss = self.loss_func(batch_output, batch_target)
            batch_loss.backward()
            self.optimizer.step()
            sum_loss += batch_loss.item()
            i_final = i
        summary['train_time'] = time.time() - start_time
        summary['train_loss'] = sum_loss / (i_final + 1)
        self.logger.debug(' Processed %i batches' % (i_final + 1))
        self.logger.info('  Training loss: %.3f' % summary['train_loss'])
        return summary

    @torch.no_grad()
    def evaluate(self, data_loader):
        """"Evaluate the model"""
        self.model.eval()
        summary = dict()
        sum_loss = 0
        sum_correct = 0
        sum_total = 0
        start_time = time.time()
        # Loop over batches
        i_final = 0 
        for i, (batch_input, batch_target) in enumerate(data_loader):
            self.logger.debug(' batch %i', i)
            batch_input = [a.to(self.device) for a in batch_input]
            batch_target = batch_target.to(self.device)
            batch_output = self.model(batch_input)
            sum_loss += self.loss_func(batch_output, batch_target).item()
            # Count number of correct predictions
            matches = ((batch_output > 0.5) == (batch_target > 0.5))
            sum_correct += matches.sum().item()
            sum_total += matches.numel()
            i_final = i
        summary['valid_time'] = time.time() - start_time
        summary['valid_loss'] = sum_loss / (i_final + 1)
        summary['valid_acc'] = sum_correct / (sum_total + 1e-10)
        self.logger.debug(' Processed %i samples in %i batches',
                          len(data_loader.sampler), i_final + 1)
        self.logger.info('  Validation loss: %.3f acc: %.3f' %
                         (summary['valid_loss'], summary['valid_acc']))
        return summary

def _test():
    t = GNNTrainer(output_dir='./')
    t.build_model()
