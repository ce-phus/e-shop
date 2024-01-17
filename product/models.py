from django.db import models

class Product(models.MOdel):
    name = models.CharField(max_length=200, blank=False, null=False)
    description= models.TextField(blank=True)
    price= models.DecimalField(default=False)
    stock= models.BooleanField(default=False)
    image = models.ImageField(null=True, blank=True)

    def __str__(self):
        return self.name
