import torch
import torch.nn as nn
import torch.optim as optim 
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
scaler_x=StandardScaler()
scaler_y=StandardScaler()

np.random.seed(42)
n_sample=1000
m=np.random.randint(1,37,n_sample)
s=np.random.randint(10,500,n_sample)
p=np.random.randint(50,2000,n_sample)
l=np.random.randint(1,365,n_sample)
x=np.column_stack((m,s,p,l))
y=np.random.randn(n_sample) * 1.5  # 加一些随机噪声（现实中的偶然波动）
r = (
    m* 0.3 +      # 每月增加0.3%损耗
    s* (-0.05) +    # 库存多，损耗反而小
    p* 0.01 +         # 单价高，精密件更敏感
    l * 0.02  # 维护越久，损耗越大
    + y
)
Y=r.reshape(-1,1)
x_train,x_test,y_train,y_test=train_test_split(x,Y,test_size=0.2,random_state=42)
#标准化
x_train=scaler_x.fit_transform(x_train)
x_test=scaler_x.transform(x_test)
y_train=scaler_y.fit_transform(y_train)
y_test=scaler_y.transform(y_test)
#转成pytorch的tensor
x_train=torch.tensor(x_train,dtype=torch.float32)
x_test=torch.tensor(x_test,dtype=torch.float32)
y_train=torch.tensor(y_train,dtype=torch.float32)
y_test=torch.tensor(y_test,dtype=torch.float32)
print("训练集大小：", x_train.shape[0])
print("测试集大小：", x_test.shape[0])
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.fc1=nn.Linear(4,64)
        self.fc2=nn.Linear(64,32)
        self.fc3=nn.Linear(32,1)
        self.relu=nn.ReLU()
    #前向传播,也就是模型的计算过程,输入x，输出预测值
    def forward(self,x):
        x=self.fc1(x)
        x=self.relu(x)
        x=self.fc2(x)
        x=self.relu(x)
        x=self.fc3(x)
        return x
model=Net()
print(model)
#定义损失函数和优化器
criterion=nn.MSELoss()
optimizer=optim.Adam(model.parameters(),lr=0.001)
epochs=200
batch_size=32
dataset=torch.utils.data.TensorDataset(x_train,y_train)
dataloader=torch.utils.data.DataLoader(dataset,batch_size=batch_size,shuffle=True)
train_losses=[]
for epoch in range(epochs):
    model.train()
    epoch_loss=0
    num_batches=0
    for batch_x,batch_y in dataloader:
        predictions=model(batch_x)
        loss=criterion(predictions,batch_y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        epoch_loss+=loss.item()
        num_batches+=1
    avg_loss=epoch_loss/num_batches
    train_losses.append(avg_loss)
    if (epoch+1)%20==0:
        print(f"第 {epoch+1} 轮，训练损失 = {avg_loss:.6f}")
#评估  
model.eval()
with torch.no_grad():
    y_pred_scaled=model(x_test)
    # 把标准化的预测值还原成原始损耗率
    y_pred = scaler_y.inverse_transform(y_pred_scaled.numpy())
    y_test_original = scaler_y.inverse_transform(y_pred_scaled.numpy())
 # 计算MSE和MAE（用刚才学的公式）
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

mse = mean_squared_error(y_test_original, y_pred)
mae = mean_absolute_error(y_test_original, y_pred)
r2 = r2_score(y_test_original, y_pred)

print("\n==================== 模型评估 ====================")
print(f"MSE (均方误差) = {mse:.4f}")
print(f"MAE (平均绝对误差) = {mae:.4f}")
print(f"R² (决定系数) = {r2:.4f}")

# ==================== 第九步：拿一条新数据做预测演示 ====================
print("\n==================== 新零件预测演示 ====================")
# 假设一个新零件：使用12个月，库存80个，单价500元，上次维护距今60天
新零件 = np.array([[12, 80, 500, 60]])
新零件_标准化 = scaler_x.transform(新零件)
新零件_张量 = torch.tensor(新零件_标准化, dtype=torch.float32)

model.eval()
with torch.no_grad():
    预测_标准化 = model(新零件_张量)
    预测_损耗率 = scaler_y.inverse_transform(预测_标准化.numpy())

print(f"新零件数据：{新零件[0]}")
print(f"预测损耗率：{预测_损耗率[0][0]:.2f}%")  




