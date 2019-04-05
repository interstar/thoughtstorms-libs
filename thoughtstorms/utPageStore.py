from PageStore import PageCollection, PageStore, WritablePageStore

import unittest

class TestPageCollection(unittest.TestCase) :
    def setUp(self) :
        self.xs = ['page1','page2','page3']
        self.col1  = PageCollection(self.xs)

    def test1(self) :
        self.assertEqual(len(self.col1),3)
        self.col1.append("page4")
        self.assertEqual(len(self.xs),3)
        self.assertEqual(len(self.col1),4)
        self.assertEqual("-".join([x for x in self.col1]), "page1-page2-page3-page4")
        self.assertEqual(type(self.col1),PageCollection)

    def test2(self) :
        self.assertEqual(self.col1.as_set(),set(self.col1))

class TestPageStore(unittest.TestCase) :

    def setUp(self) :        
        self.store = WritablePageStore("./store","md")
        

    def test1(self) :
        self.store.put("test1","This is test1")
        self.store.put("test2","This is test2")
        self.store.put("test3","Boo!")

        p = self.store.get("test1",lambda e : e, lambda e : e)
        self.assertEqual(p,"This is test1")

    def test2(self) :
        ap = self.store.all_pages()
        self.assertEqual(type(ap),PageCollection)
        self.assertEqual(ap,['test1','test2','test3'])

    def test3(self) :
        sr = self.store.search("test")
        self.assertEqual(type(sr),PageCollection)
        self.assertEqual(sr,['test1','test2'])

if __name__ == '__main__' :
    unittest.main()
