import logging
import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.models as models
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import argparse
from PIL import ImageFile
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


def test(model, test_loader, criterion, device):
    logger.info("Testing started.")
    test_loss = correct = 0

    model.to(device)
    model.eval()

    with torch.no_grad():
        for (data, target) in test_loader:
            data = data.to(device)
            target = target.to(device)

            outputs = model(data)
            loss = criterion(outputs, target)
            test_loss += loss.item()

            pred = outputs.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()

    test_loss /= len(test_loader.dataset)
    print(f"Test Loss: {test_loss:.4f}, Accuracy: {correct / len(test_loader.dataset):.2%}")
    logger.info("Testing completed.")


def train(model, train_loader, valid_loader, criterion, optimizer, epochs, device):
    logger.info("Training started.")
    for i in tqdm(range(epochs), desc="Training"):
        train_loss = 0
        model.train()

        for data, target in train_loader:
            data = data.to(device)
            target = target.to(device)

            optimizer.zero_grad()
            outputs = model(data)
            loss = criterion(outputs, target)

            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        train_loss /= len(train_loader.dataset)
        print(f"Epoch {i}: Train loss = {train_loss:.4f}")

        val_loss = 0
        model.eval()

        with torch.no_grad():
            for data, target in valid_loader:
                data = data.to(device)
                target = target.to(device)

                outputs = model(data)
                loss = criterion(outputs, target)
                val_loss += loss.item()

            val_loss /= len(valid_loader.dataset)
            print(f"Epoch {i}: Val loss = {val_loss:.4f}")

    logger.info("Training completed.")


def net(num_classes):
    logger.info("Model creation for fine-tuning started.")
    model = models.resnet50(pretrained=True)
    for param in model.parameters():
        param.requires_grad = False

    num_features = model.fc.in_features
    model.fc = nn.Linear(num_features, num_classes)
    logger.info("Model creation completed.")

    return model


def create_data_loader(data, batch_size):
    logger.info("Data loader creation started")
    data_loader = torch.utils.data.DataLoader(
        data,
        batch_size=batch_size,
        shuffle=True,
    )
    logger.info("Data loader creation completed")
    return data_loader


def create_transform(split, image_size):
    logger.info("Transformation pipeline creation started")

    pretrained_means = [0.2347, 0.2301, 0.2300]
    pretrained_stds = [0.4870, 0.4665, 0.3972]

    if split == "train":
        transforms_list = [
            transforms.Resize(image_size),
            transforms.RandomRotation(5),
            transforms.RandomHorizontalFlip(0.5),
            transforms.RandomCrop(image_size, padding=10),
            transforms.ToTensor(),
            transforms.Normalize(mean=pretrained_means, std=pretrained_stds),
        ]

    else:
        transforms_list = [
            transforms.Resize(image_size),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=pretrained_means, std=pretrained_stds),
        ]

    transformation = transforms.Compose(transforms_list)
    logger.info("Transformation pipeline creation completed")
    return transformation


def main(args):
    # Set device
    device = torch.device(args.device if torch.cuda.is_available() and args.device == "cuda" else "cpu")
    logger.info(f"Using device: {device}")

    model = net(args.num_classes)
    model.to(device)

    loss_criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=args.learning_rate)

    train_dir = os.path.join(args.data_dir, 'train')
    valid_dir = os.path.join(args.data_dir, 'valid')
    test_dir = os.path.join(args.data_dir, 'test')

    train_transform = create_transform("train", args.image_size)
    valid_transform = create_transform("valid", args.image_size)
    test_transform = create_transform("test", args.image_size)

    train_data = datasets.ImageFolder(train_dir, transform=train_transform)
    valid_data = datasets.ImageFolder(valid_dir, transform=valid_transform)
    test_data = datasets.ImageFolder(test_dir, transform=test_transform)

    train_loader = create_data_loader(train_data, args.batch_size)
    valid_loader = create_data_loader(valid_data, args.batch_size)
    test_loader = create_data_loader(test_data, args.batch_size)

    train(model, train_loader, valid_loader, loss_criterion, optimizer, args.epochs, device)

    test(model, test_loader, loss_criterion, device)

    torch.save(
        model.cpu().state_dict(),
        os.path.join(args.model_path, "model.pth")
    )
    logger.info("Model weights saved.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--num_workers", type=int, default=2)
    parser.add_argument("--num_classes", type=int, default=133)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--learning_rate", type=float, default=1e-2)
    parser.add_argument("--model_path", type=str, default=os.environ["SM_MODEL_DIR"])
    parser.add_argument("--data_dir", type=str, default=os.environ["SM_CHANNEL_TRAINING"])
    parser.add_argument("--image_size", type=int, default=224)

    args, _ = parser.parse_known_args()
    main(args)