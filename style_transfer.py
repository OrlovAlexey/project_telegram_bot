from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision.transforms as transforms
import torchvision.models as models

import copy
def style_transfer(cont_img, style_img, imsize=128, num_steps=500, start_with_white_noise=False):


    loader = transforms.Compose([
        transforms.Resize(imsize),
        transforms.CenterCrop(imsize),
        transforms.ToTensor()])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    def image_loader(image_name):
        image = Image.open(image_name)
        image = loader(image).unsqueeze(0)
        return image.to(device, torch.float)

    content_img = image_loader(cont_img)
    style_img = image_loader(style_img)

    unloader = transforms.ToPILImage()

    def imshow(tensor, title=None):
        image = tensor.cpu().clone()
        image = image.squeeze(0)
        image = unloader(image)
        image = image.convert('RGB')
        return image


    class ContentLoss(nn.Module):

        def __init__(self, target, ):
            super(ContentLoss, self).__init__()
            # we 'detach' the target content from the tree used
            # to dynamically compute the gradient: this is a stated value,
            # not a variable. Otherwise the forward method of the criterion
            # will throw an error.
            self.target = target.detach()
            self.loss = F.mse_loss(self.target, self.target)

        def forward(self, input):
            self.loss = F.mse_loss(input, self.target)
            return input

    def gram_matrix(input):
        batch_size, h, w, f_map_num = input.size()  # batch size(=1)
        # b=number of feature maps
        # (h,w)=dimensions of a feature map (N=h*w)
        features = input.view(batch_size * h, w * f_map_num)  # resise F_XL into \hat F_XL
        G = torch.mm(features, features.t())
        return G.div(batch_size * h * w * f_map_num)

    class StyleLoss(nn.Module):
        def __init__(self, target_feature):
            super(StyleLoss, self).__init__()
            self.target = gram_matrix(target_feature).detach()
            self.loss = F.mse_loss(self.target, self.target)

        def forward(self, input):
            G = gram_matrix(input)
            self.loss = F.mse_loss(G, self.target)
            return input

    cnn_normalization_mean = torch.tensor([0.485, 0.456, 0.406]).to(device)
    cnn_normalization_std = torch.tensor([0.229, 0.224, 0.225]).to(device)


    class Normalization(nn.Module):
        def __init__(self, mean, std):
            super(Normalization, self).__init__()
            # .view the mean and std to make them [C x 1 x 1] so that they can
            # directly work with image Tensor of shape [B x C x H x W].
            # B is batch size. C is number of channels. H is height and W is width.
            self.mean = mean.clone().detach().view(-1, 1, 1)
            self.std = std.clone().detach().view(-1, 1, 1)

        def forward(self, img):
            # normalize img
            return (img - self.mean) / self.std

    content_layers_default = ['conv_4']
    style_layers_default = ['conv_1', 'conv_2', 'conv_3', 'conv_4', 'conv_5']

    cnn = models.vgg19(pretrained=True).features.to(device).eval()


    def get_style_model_and_losses(cnn, normalization_mean, normalization_std,
                                   style_img, content_img,
                                   content_layers=content_layers_default,
                                   style_layers=style_layers_default):
        cnn = copy.deepcopy(cnn)

        normalization = Normalization(normalization_mean, normalization_std).to(device)

        content_losses = []
        style_losses = []


        model = nn.Sequential(normalization)

        i = 0
        for layer in cnn.children():
            if isinstance(layer, nn.Conv2d):
                i += 1
                name = 'conv_{}'.format(i)
            elif isinstance(layer, nn.ReLU):
                name = 'relu_{}'.format(i)
                layer = nn.ReLU(inplace=False)
            elif isinstance(layer, nn.MaxPool2d):
                name = 'pool_{}'.format(i)
            elif isinstance(layer, nn.BatchNorm2d):
                name = 'bn_{}'.format(i)
            else:
                raise RuntimeError('Unrecognized layer: {}'.format(layer.__class__.__name__))

            model.add_module(name, layer)

            if name in content_layers:

                target = model(content_img).detach()
                content_loss = ContentLoss(target)
                model.add_module("content_loss_{}".format(i), content_loss)
                content_losses.append(content_loss)

            if name in style_layers:

                target_feature = model(style_img).detach()
                style_loss = StyleLoss(target_feature)
                model.add_module("style_loss_{}".format(i), style_loss)
                style_losses.append(style_loss)

        for i in range(len(model) - 1, -1, -1):
            if isinstance(model[i], ContentLoss) or isinstance(model[i], StyleLoss):
                break

        model = model[:(i + 1)]

        return model, style_losses, content_losses

    def get_input_optimizer(input_img):
        optimizer = optim.LBFGS([input_img.requires_grad_()])
        return optimizer

    def run_style_transfer(cnn, normalization_mean, normalization_std,
                           content_img, style_img, input_img, num_steps=num_steps,
                           style_weight=100000, content_weight=1):

        print('Building the style transfer model..')
        model, style_losses, content_losses = get_style_model_and_losses(cnn,
                                                                         normalization_mean, normalization_std,
                                                                         style_img, content_img)
        optimizer = get_input_optimizer(input_img)

        print('Optimizing..')
        run = [0]
        while run[0] <= num_steps:

            def closure():

                optimizer.zero_grad()

                input_img.data.clamp_(0, 1)
                model(input_img)

                style_score = 0
                content_score = 0

                for sl in style_losses:
                    style_score += sl.loss
                for cl in content_losses:
                    content_score += cl.loss

                style_score *= style_weight
                content_score *= content_weight

                loss = style_score + content_score
                loss.backward()

                run[0] += 1
                if run[0] % 50 == 0:
                    print("run {}:".format(run))
                    print('Style Loss : {:4f} Content Loss: {:4f}'.format(
                        style_score.item(), content_score.item()))
                    print()

                return style_score + content_score

            optimizer.step(closure)

        input_img.data.clamp_(0, 1)

        return input_img

    if start_with_white_noise:
        input_img = torch.randn(content_img.data.size(), device=device)
    else:
        input_img = content_img.clone()

    output = run_style_transfer(cnn, cnn_normalization_mean, cnn_normalization_std,
                                content_img, style_img, input_img)

    imshow(output).save('file_2.jpg')
