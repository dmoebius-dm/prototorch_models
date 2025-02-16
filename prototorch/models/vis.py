"""Visualization Callbacks."""

import numpy as np
import pytorch_lightning as pl
import torch
import torchvision
from matplotlib import pyplot as plt
from torch.utils.data import DataLoader, Dataset

from ..utils.utils import mesh2d


class Vis2DAbstract(pl.Callback):
    def __init__(self,
                 data,
                 title="Prototype Visualization",
                 cmap="viridis",
                 border=0.1,
                 resolution=100,
                 flatten_data=True,
                 axis_off=False,
                 show_protos=True,
                 show=True,
                 tensorboard=False,
                 show_last_only=False,
                 pause_time=0.1,
                 block=False):
        super().__init__()

        if isinstance(data, Dataset):
            x, y = next(iter(DataLoader(data, batch_size=len(data))))
        elif isinstance(data, torch.utils.data.DataLoader):
            x = torch.tensor([])
            y = torch.tensor([])
            for x_b, y_b in data:
                x = torch.cat([x, x_b])
                y = torch.cat([y, y_b])
        else:
            x, y = data

        if flatten_data:
            x = x.reshape(len(x), -1)

        self.x_train = x
        self.y_train = y

        self.title = title
        self.fig = plt.figure(self.title)
        self.cmap = cmap
        self.border = border
        self.resolution = resolution
        self.axis_off = axis_off
        self.show_protos = show_protos
        self.show = show
        self.tensorboard = tensorboard
        self.show_last_only = show_last_only
        self.pause_time = pause_time
        self.block = block

    def precheck(self, trainer):
        if self.show_last_only:
            if trainer.current_epoch != trainer.max_epochs - 1:
                return False
        return True

    def setup_ax(self, xlabel=None, ylabel=None):
        ax = self.fig.gca()
        ax.cla()
        ax.set_title(self.title)
        if xlabel:
            ax.set_xlabel("Data dimension 1")
        if ylabel:
            ax.set_ylabel("Data dimension 2")
        if self.axis_off:
            ax.axis("off")
        return ax

    def plot_data(self, ax, x, y):
        ax.scatter(
            x[:, 0],
            x[:, 1],
            c=y,
            cmap=self.cmap,
            edgecolor="k",
            marker="o",
            s=30,
        )

    def plot_protos(self, ax, protos, plabels):
        ax.scatter(
            protos[:, 0],
            protos[:, 1],
            c=plabels,
            cmap=self.cmap,
            edgecolor="k",
            marker="D",
            s=50,
        )

    def add_to_tensorboard(self, trainer, pl_module):
        tb = pl_module.logger.experiment
        tb.add_figure(tag=f"{self.title}",
                      figure=self.fig,
                      global_step=trainer.current_epoch,
                      close=False)

    def log_and_display(self, trainer, pl_module):
        if self.tensorboard:
            self.add_to_tensorboard(trainer, pl_module)
        if self.show:
            if not self.block:
                plt.pause(self.pause_time)
            else:
                plt.show(block=self.block)

    def on_train_end(self, trainer, pl_module):
        plt.close()


class VisGLVQ2D(Vis2DAbstract):
    def on_epoch_end(self, trainer, pl_module):
        if not self.precheck(trainer):
            return True

        protos = pl_module.prototypes
        plabels = pl_module.prototype_labels
        x_train, y_train = self.x_train, self.y_train
        ax = self.setup_ax(xlabel="Data dimension 1",
                           ylabel="Data dimension 2")
        self.plot_data(ax, x_train, y_train)
        self.plot_protos(ax, protos, plabels)
        x = np.vstack((x_train, protos))
        mesh_input, xx, yy = mesh2d(x, self.border, self.resolution)
        _components = pl_module.proto_layer._components
        mesh_input = torch.from_numpy(mesh_input).type_as(_components)
        y_pred = pl_module.predict(mesh_input)
        y_pred = y_pred.cpu().reshape(xx.shape)
        ax.contourf(xx, yy, y_pred, cmap=self.cmap, alpha=0.35)

        self.log_and_display(trainer, pl_module)


class VisSiameseGLVQ2D(Vis2DAbstract):
    def __init__(self, *args, map_protos=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.map_protos = map_protos

    def on_epoch_end(self, trainer, pl_module):
        if not self.precheck(trainer):
            return True

        protos = pl_module.prototypes
        plabels = pl_module.prototype_labels
        x_train, y_train = self.x_train, self.y_train
        device = pl_module.device
        with torch.no_grad():
            x_train = pl_module.backbone(torch.Tensor(x_train).to(device))
            x_train = x_train.cpu().detach()
        if self.map_protos:
            with torch.no_grad():
                protos = pl_module.backbone(torch.Tensor(protos).to(device))
                protos = protos.cpu().detach()
        ax = self.setup_ax()
        self.plot_data(ax, x_train, y_train)
        if self.show_protos:
            self.plot_protos(ax, protos, plabels)
            x = np.vstack((x_train, protos))
            mesh_input, xx, yy = mesh2d(x, self.border, self.resolution)
        else:
            mesh_input, xx, yy = mesh2d(x_train, self.border, self.resolution)
        _components = pl_module.proto_layer._components
        mesh_input = torch.Tensor(mesh_input).type_as(_components)
        y_pred = pl_module.predict_latent(mesh_input,
                                          map_protos=self.map_protos)
        y_pred = y_pred.cpu().reshape(xx.shape)
        ax.contourf(xx, yy, y_pred, cmap=self.cmap, alpha=0.35)

        self.log_and_display(trainer, pl_module)


class VisCBC2D(Vis2DAbstract):
    def on_epoch_end(self, trainer, pl_module):
        if not self.precheck(trainer):
            return True

        x_train, y_train = self.x_train, self.y_train
        protos = pl_module.components
        ax = self.setup_ax(xlabel="Data dimension 1",
                           ylabel="Data dimension 2")
        self.plot_data(ax, x_train, y_train)
        self.plot_protos(ax, protos, "w")
        x = np.vstack((x_train, protos))
        mesh_input, xx, yy = mesh2d(x, self.border, self.resolution)
        _components = pl_module.components_layer._components
        y_pred = pl_module.predict(
            torch.Tensor(mesh_input).type_as(_components))
        y_pred = y_pred.cpu().reshape(xx.shape)

        ax.contourf(xx, yy, y_pred, cmap=self.cmap, alpha=0.35)

        self.log_and_display(trainer, pl_module)


class VisNG2D(Vis2DAbstract):
    def on_epoch_end(self, trainer, pl_module):
        if not self.precheck(trainer):
            return True

        x_train, y_train = self.x_train, self.y_train
        protos = pl_module.prototypes
        cmat = pl_module.topology_layer.cmat.cpu().numpy()

        ax = self.setup_ax(xlabel="Data dimension 1",
                           ylabel="Data dimension 2")
        self.plot_data(ax, x_train, y_train)
        self.plot_protos(ax, protos, "w")

        # Draw connections
        for i in range(len(protos)):
            for j in range(i, len(protos)):
                if cmat[i][j]:
                    ax.plot(
                        [protos[i, 0], protos[j, 0]],
                        [protos[i, 1], protos[j, 1]],
                        "k-",
                    )

        self.log_and_display(trainer, pl_module)


class VisImgComp(Vis2DAbstract):
    def __init__(self,
                 *args,
                 random_data=0,
                 dataformats="CHW",
                 num_columns=2,
                 add_embedding=False,
                 embedding_data=100,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.random_data = random_data
        self.dataformats = dataformats
        self.num_columns = num_columns
        self.add_embedding = add_embedding
        self.embedding_data = embedding_data

    def on_train_start(self, trainer, pl_module):
        tb = pl_module.logger.experiment
        if self.add_embedding:
            ind = np.random.choice(len(self.x_train),
                                   size=self.embedding_data,
                                   replace=False)
            data = self.x_train[ind]
            # print(f"{data.shape=}")
            # print(f"{self.y_train[ind].shape=}")
            tb.add_embedding(data.view(len(ind), -1),
                             label_img=data,
                             global_step=None,
                             tag="Data Embedding",
                             metadata=self.y_train[ind],
                             metadata_header=None)

        if self.random_data:
            ind = np.random.choice(len(self.x_train),
                                   size=self.random_data,
                                   replace=False)
            data = self.x_train[ind]
            grid = torchvision.utils.make_grid(data, nrow=self.num_columns)
            tb.add_image(tag="Data",
                         img_tensor=grid,
                         global_step=None,
                         dataformats=self.dataformats)

    def add_to_tensorboard(self, trainer, pl_module):
        tb = pl_module.logger.experiment

        components = pl_module.components
        grid = torchvision.utils.make_grid(components, nrow=self.num_columns)
        tb.add_image(
            tag="Components",
            img_tensor=grid,
            global_step=trainer.current_epoch,
            dataformats=self.dataformats,
        )

    def on_epoch_end(self, trainer, pl_module):
        if not self.precheck(trainer):
            return True

        if self.show:
            components = pl_module.components
            grid = torchvision.utils.make_grid(components,
                                               nrow=self.num_columns)
            plt.imshow(grid.permute((1, 2, 0)).cpu(), cmap=self.cmap)

        self.log_and_display(trainer, pl_module)
