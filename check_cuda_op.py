import torch
try:
    print(f"Testing CUDA on {torch.cuda.get_device_name(0)}")
    x = torch.rand(5, 3).cuda()
    y = torch.rand(5, 3).cuda()
    z = x + y
    print("Tensor operation successful:")
    print(z)
except Exception as e:
    print(f"Tensor operation FAILED: {e}")
