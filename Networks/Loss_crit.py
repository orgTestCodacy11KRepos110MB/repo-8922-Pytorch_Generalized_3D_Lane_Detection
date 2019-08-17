# -*- coding: utf-8 -*-
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable


class Laneline_3D_loss(nn.Module):
    """
    compute the loss between predicted 3D lanelines in anchor representation,
    and the ground-truth 3D lanelines in anchor representation.
    loss = loss1 + loss2 + loss2
    loss1: cross entropy loss for lane type classification
    loss2: sum of geometric distance betwen 3D lane anchor points in X and Z offsets
    loss3: error in estimating pitch and camera heights
    """
    def __init__(self, num_types, anchor_dim, fix_cam):
        super(Laneline_3D_loss, self).__init__()
        self.num_types = num_types
        self.anchor_dim = anchor_dim
        self.fix_cam = fix_cam

    def forward(self, pred_3D_lanes, gt_3D_lanes, pred_hcam, gt_hcam, pred_pitch, gt_pitch):
        """

        :param pred_3D_lanes: predicted tensor with size N x (ipm_w/8) x 3*(2*K+1)
        :param gt_3D_lanes: ground-truth tensor with size N x (ipm_w/8) x 3*(2*K+1)
        :param pred_pitch: predicted pitch with size N
        :param gt_pitch: ground-truth pitch with size N
        :param pred_hcam: predicted camera height with size N
        :param gt_hcam: ground-truth camera height with size N
        :return:
        """
        sizes = pred_3D_lanes.shape
        # reshape to N x ipm_w/8 x 3 x (2K+1)
        pred_3D_lanes = pred_3D_lanes.reshape(sizes[0], sizes[1], self.num_types, self.anchor_dim)
        gt_3D_lanes = gt_3D_lanes.reshape(sizes[0], sizes[1], self.num_types, self.anchor_dim)
        # class prob N x ipm_w/8 x 3 x 1, anchor value N x ipm_w/8 x 3 x 2K
        pred_class = pred_3D_lanes[:, :, :, -1].unsqueeze(-1)
        pred_anchors = pred_3D_lanes[:, :, :, :-1]
        gt_class = gt_3D_lanes[:, :, :, -1].unsqueeze(-1)
        gt_anchors = gt_3D_lanes[:, :, :, :-1]

        loss1 = -torch.sum(gt_class*torch.log(pred_class) +
                           (torch.ones_like(gt_class)-gt_class)*torch.log((torch.ones_like(pred_class)-pred_class)))
        # applying L1 norm does not need to separate X and Z
        loss2 = torch.sum(torch.norm(gt_class*(pred_anchors-gt_anchors), p=1, dim=3))
        if self.fix_cam:
            return loss1+loss2
        loss3 = torch.sum(torch.abs(gt_pitch-pred_pitch))+torch.sum(torch.abs(gt_hcam-pred_hcam))
        return loss1+loss2+loss3


# unit test
if __name__ == '__main__':
    num_types = 3
    anchor_dim = 13
    fix_cam = True
    criterion = Laneline_3D_loss(num_types, anchor_dim, fix_cam)
    criterion = criterion.cuda()

    pred_3D_lanes = torch.rand(8, 26, num_types*anchor_dim).cuda()
    gt_3D_lanes = torch.rand(8, 26, num_types*anchor_dim).cuda()
    pred_pitch = torch.ones(8).float().cuda()
    gt_pitch = torch.ones(8).float().cuda()
    pred_hcam = torch.ones(8).float().cuda()
    gt_hcam = torch.ones(8).float().cuda()

    loss = criterion(pred_3D_lanes, gt_3D_lanes, pred_pitch, gt_pitch, pred_hcam, gt_hcam)

    print(loss)
